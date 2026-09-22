# Командная строка

После установки команда `praatfigure` без подкоманды открывает GUI.

## Один пример

```bash
praatfigure render \
  --audio example.wav \
  --textgrid example.TextGrid \
  --tier phones \
  --label "ə" \
  --padding-left 0.1 \
  --padding-right 0.1 \
  --output figure.svg
```

## Пакетная обработка

```bash
praatfigure batch \
  --audio example.wav \
  --textgrid example.TextGrid \
  --tier phones \
  --regex "^[aeiouə]$" \
  --output-dir figures
```

## Сохранённый проект

```bash
praatfigure render-project example.praatfig.json --output figure.pdf
```

Добавьте `--overwrite`, если существующий выходной файл можно заменить. Полный
актуальный список аргументов выводит `praatfigure --help` и справка конкретной
команды, например `praatfigure render --help`.

