# Сборка и публикация

Документация хранится в каталоге `docs/` того же репозитория. Так изменения
интерфейса и инструкции проходят review и выпускаются вместе с кодом.

## Локальная разработка

```bash
python -m venv .venv
python -m pip install -e ".[all,dev,build,docs]"
python -m pytest -q
mkdocs serve
```

## Локальная сборка приложения

PyInstaller собирает приложение только для той ОС, на которой он запущен:

```bash
pyinstaller --noconfirm --clean packaging/PraatFigure.spec
```

Результат появляется в `dist/`. Windows-установщик дополнительно компилируется
Inno Setup из `packaging/windows/PraatFigure.iss`. macOS DMG и Linux AppImage
формируются командами из workflow `Build installers`.

## GitHub Actions

- **Tests** проверяет Windows, macOS и Linux при push и pull request.
- **Build installers** можно запустить вручную на вкладке Actions.
- push тега `v0.1.0` запускает сборку и создаёт GitHub Release с установщиками.
- **Documentation** собирает и публикует этот сайт при изменениях ветки `main`.

Для первого развёртывания Pages откройте **Settings → Pages** и выберите
**GitHub Actions** как источник. После этого workflow не требует отдельной ветки
`gh-pages`.

## Первый push

Если каталог ещё не является Git-репозиторием:

```bash
git init
git add .
git commit -m "Initial PraatFigure release"
git branch -M main
git remote add origin https://github.com/USER/REPOSITORY.git
git push -u origin main
```

Для выпуска версии обновите номер в `pyproject.toml`, создайте и отправьте тег:

```bash
git tag v0.1.0
git push origin v0.1.0
```

Автоматические артефакты пока не подписываются. Для публичного выпуска без
предупреждений ОС понадобятся Windows code-signing certificate и Apple
Developer ID с notarization; секреты нельзя добавлять непосредственно в код.

