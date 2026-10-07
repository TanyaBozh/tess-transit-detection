# Как запустить Python-код в окружении `tess-eleanor`

Эта инструкция предназначена для запуска Python-кода, использующего `eleanor` и библиотеки из рабочего окружения проекта.

## 1. Где находится виртуальное окружение

Наше виртуальное окружение находится отдельно от папок с кодом:

```text
D:\venvs\tess-eleanor
```

Папка с кодом может находиться в любом другом месте. Например:

```text
D:\Photometry\My_Project\tess-transit-detection
```

Это нормально. **Не нужно копировать виртуальное окружение в папку проекта.**

## 2. Открыть проект в VS Code

1. Запустить VS Code.
2. Открыть папку, в которой находится нужный Python-файл.

## 3. Открыть терминал

В VS Code выбрать:

**Terminal → New Terminal**

Для нашего окружения лучше использовать **Command Prompt (cmd)**.

Если открылся PowerShell, выбери:

**Terminal → New Terminal → Command Prompt**

В терминале должно быть примерно:

```text
D:\Photometry\My_Project\tess-transit-detection>
```

## 4. Активировать окружение

Выполнить:

```cmd
D:\venvs\tess-eleanor\Scripts\activate.bat
```

После успешной активации в начале строки появится:

```text
(tess-eleanor)
```

Например:

```text
(tess-eleanor) D:\Photometry\My_Project\tess-transit-detection>
```

Это означает, что виртуальное окружение активно.

## 5. Проверить Python

Выполнить:

```cmd
python --version
```

Ожидаемый результат:

```text
Python 3.10.11
```

## 6. Проверить `eleanor`

Выполнить:

```cmd
python -c "import eleanor; print(eleanor.__version__)"
```

Ожидаемый результат:

```text
2.0.5
```

## 7. Запустить Python-файл

Если нужный файл находится в текущей папке, например:

```text
test_eleanor.py
```

запустить его:

```cmd
python test_eleanor.py
```

Если файл находится в подпапке:

```cmd
python src\test_eleanor.py
```

## 8. Как проверить, какой именно Python используется

Если есть сомнения, выполнить:

```cmd
python -c "import sys; print(sys.executable)"
```

Должен появиться путь:

```text
D:\venvs\tess-eleanor\Scripts\python.exe
```

Это самая надёжная проверка.

## 9. Короткая памятка

Каждый раз, когда нужно запустить код:

1. Открыть папку проекта в VS Code.
2. Открыть **Command Prompt**:
   **Terminal → New Terminal → Command Prompt**.
3. Активировать окружение:

```cmd
D:\venvs\tess-eleanor\Scripts\activate.bat
```

4. Убедиться, что появилось `(tess-eleanor)`.
5. Запустить файл:

```cmd
python имя_файла.py
```

При необходимости проверить:

```cmd
python --version
python -c "import eleanor; print(eleanor.__version__)"
```

## 10. Почему используется Command Prompt

В нашей системе ранее PowerShell блокировал запуск `Activate.ps1` из-за политики выполнения скриптов.

Поэтому для этого окружения используем:

```cmd
D:\venvs\tess-eleanor\Scripts\activate.bat
```

в **Command Prompt (cmd)**.

Не нужно менять системную политику Windows только ради активации этого окружения.

## 11. Где находится окружение и где находится код

```text
Папка проекта с кодом
D:\Photometry\My_Project\tess-transit-detection
│
├── *.py
├── *.ipynb
├── README.md
└── ...
        │
        │ использует
        ↓
Виртуальное окружение
D:\venvs\tess-eleanor
│
├── Python 3.10.11
├── eleanor 2.0.5
├── TensorFlow 2.10.1
├── photutils 1.11.0
├── lightkurve 2.4.2
└── другие библиотеки
```

Папка проекта и виртуальное окружение могут находиться в совершенно разных местах.

## 12. Выйти из окружения

Когда работа закончена:

```cmd
deactivate
```

После этого `(tess-eleanor)` исчезнет из начала строки терминала.

При следующем запуске проекта окружение нужно активировать снова:

```cmd
D:\venvs\tess-eleanor\Scripts\activate.bat
```
