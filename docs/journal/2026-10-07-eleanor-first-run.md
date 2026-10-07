\# 2026-10-07 — Первый успешный запуск eleanor



\## Продолжение журнала



Сегодня после подготовки окружения был доведён до рабочего состояния первый запуск `eleanor` на реальных данных TESS.



\### 1. Диагностика доступа к STScI



При запуске `lightcurve\_eleanor.py` `eleanor.Source()` сначала завершался SSL-ошибкой.



Проверки показали:



\* `requests` успешно подключается к STScI;

\* `astroquery.mast.Tesscut` успешно работает;

\* проблема возникает именно в `urllib.request.urlopen()`, который использует `eleanor.update`.



В исходном коде `eleanor 2.0.5` найдено:



```python

from urllib.request import urlopen



def update\_max\_sector():

&#x20;   baseurl = "https://archive.stsci.edu/missions/tess/ffi/"

&#x20;   page = urlopen(baseurl)

&#x20;   ...

```



\### 2. Workaround



Установленный пакет `eleanor` не изменялся.



В скрипте используется локальная замена `eleanor.update.urlopen` на функцию через `requests`:



```python

import io

import requests

import eleanor.update



def \_requests\_urlopen(url, \*args, \*\*kwargs):

&#x20;   response = requests.get(url, timeout=30)

&#x20;   response.raise\_for\_status()

&#x20;   return io.BytesIO(response.content)



eleanor.update.urlopen = \_requests\_urlopen

```



Проверка:



```text

Most recent sector available = 99

```



\### 3. Подготовка metadata сектора 11



Для тестовой звезды TIC 8636 был использован сектор 11.



Запуск:



```python

eleanor.update.Update(sector=11)

```



успешно выполнил:



1\. загрузку TESSCut cutout;

2\. `get\_target()`;

3\. `get\_cadences()`;

4\. `get\_quality()`;

5\. `get\_cbvs()`.



Финальный результат:



```text

Success! Sector 11 now available.

```



Это устранило предыдущую ошибку `FileNotFoundError` для metadata сектора, в частности `cadences\_s0011.txt`.



Во время этапа CBV несколько раз появилось сообщение Windows curl/schannel:



```text

CRYPT\_E\_REVOCATION\_OFFLINE

```



Оно не остановило `Update`, поэтому пока отдельно не исправлялось.



\### 4. Первый успешный запуск



После создания metadata был повторно запущен:



```cmd

python lightcurve\_eleanor.py

```



Запуск завершился успешно.



Таким образом, впервые полностью прошёл путь:



```text

каталог

&#x20; ↓

TIC + сектор

&#x20; ↓

eleanor.Source()

&#x20; ↓

TESSCut → TPF

&#x20; ↓

eleanor.Update()

&#x20; ↓

metadata сектора

&#x20; ↓

eleanor.TargetData()

&#x20; ↓

фотометрия

&#x20; ↓

raw / corrected / PCA flux

&#x20; ↓

графики

```



\### 5. Что делает текущий скрипт



`lightcurve\_eleanor.py`:



1\. читает каталог;

2\. выбирает TIC и сектор;

3\. создаёт `eleanor.Source`;

4\. получает TESSCut TPF;

5\. создаёт `eleanor.TargetData`;

6\. оставляет точки с `quality == 0`;

7\. извлекает варианты flux;

8\. нормирует их относительно медианы;

9\. строит графики TPF и кривых блеска.



Сейчас сохраняются варианты:



\* `raw\_flux`;

\* `corr\_flux`;

\* `pca\_flux`;

\* `psf\_flux`, если он доступен.



\### Результат дня



Окружение `Python 3.10.11 + eleanor 2.0.5` работает, доступ к TESSCut проверен, metadata сектора 11 созданы, а `lightcurve\_eleanor.py` впервые успешно построил кривые блеска.



Следующий этап — разобраться, что именно происходит внутри `Source` и `TargetData`, и определить, какой вариант кривой блеска лучше подходит для дальнейшего ML-пайплайна.



