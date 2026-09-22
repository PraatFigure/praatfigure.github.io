# Установка

## Готовые приложения

Откройте страницу **Releases** репозитория и скачайте файл для своей системы.

### Windows

Запустите `PraatFigure-…-Windows-x64-Setup.exe`. Установщик добавляет программу
в меню «Пуск» и по желанию создаёт ярлык на рабочем столе.

Текущие автоматические сборки не подписаны коммерческим сертификатом. Поэтому
Windows SmartScreen может показать предупреждение для новой версии. Проверяйте,
что файл скачан именно со страницы Releases проекта.

### macOS

Откройте DMG для своей архитектуры и перенесите PraatFigure в Applications:

- `macOS-arm64` — Apple Silicon (M1 и новее);
- `macOS-x86_64` — компьютеры Mac с Intel.

Пока приложение не нотаризовано Apple, первый запуск может потребовать
разрешения в **System Settings → Privacy & Security**.

### Linux

Сделайте AppImage исполняемым и запустите его:

```bash
chmod +x PraatFigure-*-Linux-x86_64.AppImage
./PraatFigure-*-Linux-x86_64.AppImage
```

Также в Release имеется переносимый `.tar.gz`. После распаковки запускайте
`PraatFigure/PraatFigure`.

## Установка из исходного кода

Требуется Python 3.12.

```bash
python -m venv .venv
```

Windows:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[all]"
.\run_praatfigure.ps1
```

macOS и Linux:

```bash
source .venv/bin/activate
python -m pip install -e ".[all]"
praatfigure
```

Локальное виртуальное окружение особенно полезно в Windows: оно изолирует Qt от
несовместимых DLL, которые могли добавить в `PATH` Conda или другие программы.
