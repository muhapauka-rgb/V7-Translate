# Карта интерфейса

Интерфейс написан на `Python + PySide6 (Qt)`.

## Где что лежит

- Логика и структура окна:
  `/Users/ponch/V7 Translate/app/ui/main_window.py`
- Внешний вид, цвета, рамки, кнопки, поля:
  `/Users/ponch/V7 Translate/app/ui/main_window.qss`

## Что проще всего менять

Если нужно поменять дизайн, обычно трогают файл:

`/Users/ponch/V7 Translate/app/ui/main_window.qss`

Там можно менять:

- фон окна;
- цвета кнопок;
- скругления;
- рамки блоков;
- размеры текста;
- внешний вид полей;
- цвет и стиль прогресс-бара.

## Основные блоки окна

- Заголовок приложения:
  `#titleLabel`
- Подзаголовок:
  `#subtitleLabel`
- Блок выбора файла:
  `#fileGroup`
- Блок информации об аудио:
  `#audioInfoGroup`
- Блок настроек:
  `#optionsGroup`
- Блок хода выполнения:
  `#progressGroup`
- Основные кнопки:
  `#primaryButton`
- Вторичная кнопка:
  `#secondaryButton`
- Кнопка отмены:
  `#mutedButton`
- Индикатор прогноза:
  `#estimateLabel`
- Поле журнала:
  `#logOutput`

## Что говорить Codex/ChatGPT

Если захотите менять дизайн в чате, можно писать примерно так:

"Измени дизайн файла `/Users/ponch/V7 Translate/app/ui/main_window.qss`.
Сделай стиль более современным, светлым, с мягкими тенями, крупнее кнопки и более аккуратный блок прогресса.
Логику в `main_window.py` не трогай."

Или так:

"Переделай интерфейс в стиле minimal macOS.
Меняй только:
`/Users/ponch/V7 Translate/app/ui/main_window.qss`
и при необходимости objectName в
`/Users/ponch/V7 Translate/app/ui/main_window.py`."
