# `main/core` — тема сайта и шаблоны кастомной админки

Публичная тема, шаблоны админки, собранная статика и сторонние ассеты.

## Структура

- [theme/default/](theme/default/) — публичная тема: `views/*.html` как шаблоны Django, `js/`, `css/`, `images/`.
- Форма регистрации на игру — один экземпляр: [theme/default/views/components/register_game_popup.html](theme/default/views/components/register_game_popup.html) (подключается в `home.html` и `schedule.html`); `id` полей не дублируются.
- [admin/](admin/) — шаблоны и стили кастомной админки (`main/admin/`, не `django.contrib.admin`).
- [libs/](libs/) — сторонние ассеты.

## Правки в этом репозитории

- Работаем **только** в `main/core/` (шаблоны, `css/`, `js/`, изображения). Каталог `#src/` не редактировать.
- CSS правим в `core/**/css/` напрямую. **Не ломай пути** без обновления шаблонов.

## Контракт с Python

- Пути к шаблонам должны совпадать с настройками `TEMPLATES['DIRS']` в [main/main/settings.py](../main/settings.py) и вызовами `render()` в приложениях.

## Медиа

- Загружаемые пользователем файлы — в `main/media/`, **не путать** со статикой темы.
