"""
Способ 2: кривые блеска, построенные самостоятельно из FFI через eleanor.

Порядок действий: по TIC и номеру сектора вырезается TPF из полнокадровых
снимков (TESSCut), затем eleanor считает по нему апертурную фотометрию.

Модуль самодостаточен: сам читает каталог и сам рисует результат.
При запуске напрямую (`python lightcurve_eleanor.py`) ничего не сохраняет —
только выводит графики в окно. Сохранением занимается lightcurve_compare.py.
"""

import os
import io
import warnings
import requests

import numpy as np
import pandas as pd

warnings.filterwarnings('ignore')

import eleanor  # noqa: E402
from eleanor.maxsector import maxsector  # noqa: E402

# Временный workaround для Windows:
# eleanor.update использует urllib.request.urlopen(),
# который в данном окружении не может установить HTTPS-соединение
# с archive.stsci.edu. requests работает нормально.

import eleanor.update

_original_urlopen = eleanor.update.urlopen

def _requests_urlopen(url, *args, **kwargs):
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return io.BytesIO(response.content)

eleanor.update.urlopen = _requests_urlopen

# ============================================================
# НАСТРОЙКИ ПО УМОЛЧАНИЮ
# ============================================================
CATALOG = os.path.join('data', 'eb_catalog_with_sectors.csv')

TPF_HEIGHT = 15         # размер вырезаемого TPF, пиксели
TPF_WIDTH = 15
TESSCUT_SIZE = 31       # размер выреза TESSCut; из него же считается фон
BKG_SIZE = 31           # окно фона, не больше TESSCUT_SIZE
USE_TESSCUT = True      # True — сразу TESSCut, False — сначала искать постакарды eleanor
# PSF-моделирование (TensorFlow 1.15) выключено по результатам проверки:
# eleanor подгоняет профиль ОДНОГО источника, а не раскладывает кадр на цель
# и соседку, поэтому от блендинга не спасает, зато свободные параметры подгонки
# впитывают собственную переменность звезды. Измерено: у TIC 890432 глубина
# главного затмения падала с 14.3% по каталогу до 2.0%, у TIC 672717 — с 12.1%
# до 4.3%. Ещё на 3 звёздах из 10 подгонка расходилась (до 1918 медиан).
# Для каталога затменных двойных это опасный артефакт: занижает глубины.
DO_PSF = False
DO_PCA = True           # даёт дополнительный вариант потока data.pca_flux

# eleanor 2.0.5 умеет секторы только до maxsector (=51). Более поздние он
# не обработает: в update.py нет ветки для 200-секундного каденса (с сектора 56).
MAX_SECTOR = maxsector


# ============================================================
# ЧТЕНИЕ КАТАЛОГА
# ============================================================
def read_catalog(path=CATALOG, n_stars=5, sector_pick='lowest', max_sector=MAX_SECTOR,
                 available=None):
    """Отбирает из каталога первые n_stars РАЗНЫХ TIC, по одному сектору на каждый.

    Параметры
    ---------
    path : str
        Путь к eb_catalog_with_sectors.csv.
    n_stars : int
        Сколько разных звёзд взять.
    sector_pick : {'lowest', 'highest', 'both'}
        Какой из доступных секторов выбрать:
          'lowest'  — самый ранний;
          'highest' — самый поздний (обычно каденс 10 мин вместо 30);
          'both'    — самый поздний из тех, где есть данные В ОБОИХ архивах.
        Режим 'both' нужен потому, что поздний сектор часто пуст на MAST:
        eleanor построит кривую, а сравнивать её будет не с чем. Он требует
        callback `available`, иначе функция не знает, что лежит на MAST.
    max_sector : int
        Верхняя граница номера сектора; по умолчанию лимит eleanor.
        Звёзды без подходящего сектора пропускаются.

    Возвращает
    ----------
    list[dict] с ключами tic, sector, ra, dec, tmag, period, depth, cadence_min.
    """
    df = pd.read_csv(path)
    targets = []

    for tic in df['TIC'].drop_duplicates():
        rows = df[df['TIC'] == tic]
        if max_sector is not None:
            rows = rows[rows['Sector'] <= max_sector]
        if len(rows) == 0:
            print('   ⏭️  TIC %d: нет секторов <= %s, пропускаем' % (tic, max_sector))
            continue

        if sector_pick == 'both':
            if available is None:
                raise ValueError("sector_pick='both' требует callback available: "
                                 "функцию (tic, sector) -> bool. Передайте, "
                                 "например, lightcurve_mast.has_mast_product")
            # Идём от позднего сектора к раннему и берём первый, который есть
            # в обоих архивах: так каденс максимален, но сравнение сохраняется.
            row = None
            for _, candidate in rows.sort_values('Sector', ascending=False).iterrows():
                if available(int(candidate['TIC']), int(candidate['Sector'])):
                    row = candidate
                    break
            if row is None:
                print('   ⏭️  TIC %d: ни в одном секторе нет данных сразу в двух '
                      'архивах, пропускаем' % tic)
                continue
        else:
            rows = rows.sort_values('Sector', ascending=(sector_pick == 'lowest'))
            row = rows.iloc[0]
        targets.append({
            # int() обязателен: eleanor.Source проверяет тип строго (type(...) == int),
            # numpy.int64 из pandas проверку не проходит, и eleanor падает
            # с сообщением «TESS has not (yet) observed your target»
            'tic': int(row['TIC']),
            'sector': int(row['Sector']),
            'ra': float(row['RA']),
            'dec': float(row['DEC']),
            'tmag': float(row['Tmag']),
            'period': float(row['Period']),
            'depth': float(row['Depth_pri']),
            'cadence_min': float(row['Cadence_min']),
        })
        if len(targets) == n_stars:
            break

    return targets


# ============================================================
# ВЫРЕЗАНИЕ TPF И ФОТОМЕТРИЯ
# ============================================================
def cut_tpf(tic, sector, tesscut_size=TESSCUT_SIZE, use_tesscut=USE_TESSCUT, verbose=True):
    """Находит звезду и вырезает её окрестность из FFI.

    Возвращает объект eleanor.Source (в нём уже определены сектор, камера, чип).
    """
    star = eleanor.Source(tic=tic, sector=sector, tc=use_tesscut,
                          tesscut_size=tesscut_size)
    if verbose:
        print('   ✂️  eleanor: TIC %s, сектор %s, камера %s, чип %s'
              % (star.tic, star.sector, star.camera, star.chip))
    return star


def lightcurve_from_eleanor(tic, sector, height=TPF_HEIGHT, width=TPF_WIDTH,
                            bkg_size=BKG_SIZE, tesscut_size=TESSCUT_SIZE,
                            do_psf=DO_PSF, do_pca=DO_PCA, verbose=True):
    """Строит кривую блеска из FFI: вырезает TPF и считает по нему фотометрию.

    Параметры
    ---------
    tic, sector : int
        Идентификатор звезды и номер сектора (оба должны быть именно int).
    height, width : int
        Размер вырезаемого TPF в пикселях.
    bkg_size : int
        Окно оценки фона. Больше — лучше оценка фона, но можно захватить соседние звёзды.
    do_psf, do_pca : bool
        Включать ли PSF-моделирование и PCA-коррекцию.

    Возвращает
    ----------
    (time, fluxes, data), где fluxes — словарь нормированных потоков
    ('raw', 'corr', и при наличии 'pca', 'psf'), а data — eleanor.TargetData.
    """
    star = cut_tpf(tic, sector, tesscut_size=tesscut_size, verbose=verbose)

    data = eleanor.TargetData(star, height=height, width=width, bkg_size=bkg_size,
                              do_psf=do_psf, do_pca=do_pca)

    good = data.quality == 0          # отбрасываем кадры с флагами качества
    time = np.asarray(data.time, dtype=float)[good]

    fluxes = {}
    for name, attr in (('raw', 'raw_flux'), ('corr', 'corr_flux'),
                       ('pca', 'pca_flux'), ('psf', 'psf_flux')):
        arr = getattr(data, attr, None)
        if arr is None:
            continue
        arr = np.asarray(arr, dtype=float)[good]
        median = np.nanmedian(arr)
        if np.isfinite(median) and median != 0:
            fluxes[name] = arr / median

    if 'corr' not in fluxes:
        raise RuntimeError('eleanor не вернул corrected flux')

    if verbose:
        print('   ✅ eleanor: %d хороших кадров из %d, потоки: %s'
              % (len(time), len(data.time), ', '.join(fluxes)))
    return time, fluxes, data


# ============================================================
# ОТРИСОВКА (только в окно, без сохранения)
# ============================================================
def plot_tpf(ax, data, height=TPF_HEIGHT, width=TPF_WIDTH):
    """Показывает первый кадр TPF в логарифмической шкале и контур апертуры."""
    ax.imshow(np.log10(np.clip(data.tpf[0], 1, None)), origin='lower', cmap='viridis')
    if getattr(data, 'aperture', None) is not None:
        ax.contour(data.aperture, levels=[0.5], colors='red', linewidths=1.5)
    ax.set_title('TPF из FFI %dx%d (log)' % (height, width), fontsize=10)
    ax.set_xlabel('Колонка (пиксели)')
    ax.set_ylabel('Строка (пиксели)')


def plot_lightcurve(ax, target, time, fluxes):
    """Рисует кривую блеска eleanor: сырой поток серым, скорректированный синим."""
    if 'raw' in fluxes:
        ax.plot(time, fluxes['raw'], '.', ms=1.5, color='0.75', label='raw')
    ax.plot(time, fluxes['corr'], '.', ms=1.5, color='tab:blue', label='corrected')
    ax.legend(loc='best', markerscale=6, fontsize=8)
    ax.set_title('TIC %d, сектор %d — eleanor' % (target['tic'], target['sector']),
                 fontsize=10)
    ax.set_xlabel('Время (BTJD, дни)')
    ax.set_ylabel('Норм. поток')


def main(catalog=CATALOG, n_stars=5, sector_pick='lowest', max_sector=MAX_SECTOR):
    """Строит кривые блеска через eleanor и показывает их в окне. Ничего не сохраняет.

    sector_pick='both' здесь работать не будет: этот модуль про MAST ничего
    не знает и знать не должен. Кросс-архивный отбор живёт в lightcurve_compare.py,
    который передаёт сюда callback lightcurve_mast.has_mast_product.
    """
    import matplotlib.pyplot as plt

    print('📖 Читаем каталог %s' % catalog)
    targets = read_catalog(catalog, n_stars=n_stars,
                           sector_pick=sector_pick, max_sector=max_sector)
    print('✅ Отобрано звёзд: %d (eleanor поддерживает секторы <= %s)\n'
          % (len(targets), max_sector))

    fig, axes = plt.subplots(len(targets), 2, figsize=(12, 2.8 * len(targets)),
                             gridspec_kw={'width_ratios': [1, 3]})
    axes = np.atleast_2d(axes)

    for row, target in zip(axes, targets):
        print('⭐ TIC %d, сектор %d' % (target['tic'], target['sector']))
        try:
            time, fluxes, data = lightcurve_from_eleanor(target['tic'], target['sector'])
            plot_tpf(row[0], data)
            plot_lightcurve(row[1], target, time, fluxes)
        except Exception as e:
            print('   ❌ %s' % e)
            for ax in row:
                ax.text(0.5, 0.5, 'TIC %d: кривая не получена' % target['tic'],
                        ha='center', va='center', transform=ax.transAxes, color='red')
                ax.set_axis_off()

    fig.suptitle('Способ 2: кривые блеска из FFI через eleanor', fontsize=13)
    fig.tight_layout()
    plt.show()          # результат только на экран


if __name__ == '__main__':
    main()
