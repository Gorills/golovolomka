# `main/core` — тема сайта и шаблоны кастомной админки

Публичная тема, шаблоны админки, собранная статика и сторонние ассеты.

## Структура

- [theme/default/](theme/default/) — публичная тема: `views/*.html` как шаблоны Django, `js/`, `css/`, `images/`.
- Форма регистрации на игру — один экземпляр: [theme/default/views/components/register_game_popup.html](theme/default/views/components/register_game_popup.html) (подключается в `home.html` и `schedule.html`); `id` полей не дублируются.
- [admin/](admin/) — шаблоны и стили кастомной админки (`main/admin/`, не `django.contrib.admin`).
- [libs/](libs/) — сторонние ассеты.

## Сборка

- SCSS/исходники могут жить в `#src/` в корне репозитория; скомпилированный CSS — в `core/**/css/`. **Не ломай пути без обновления шаблонов**.
- При правке исходников в `#src/` — убедись, что сборка прошла и скомпилированные файлы попали в `core/`.

## Контракт с Python

- Пути к шаблонам должны совпадать с настройками `TEMPLATES['DIRS']` в [main/main/settings.py](../main/settings.py) и вызовами `render()` в приложениях.

## Медиа

- Загружаемые пользователем файлы — в `main/media/`, **не путать** со статикой темы.
