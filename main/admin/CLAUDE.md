# `main/admin` — кастомная админка (НЕ `django.contrib.admin`)

**Важно**: это отдельное приложение с именем `admin` в `INSTALLED_APPS`. Стандартный `django.contrib.admin` отключён. Не путать с официальной админкой Django.

## Ответственность

CRUD для заказов, игр, корпоративных блоков, франшизы, настроек кодов/цветов/темы, поддоменов и т.д. Маршруты висят на префиксе `/admin/`.

## Ключевые файлы

- [urls.py](urls.py) — длинный список `path()` для разделов админки.
- [views.py](views.py) — вьюхи; по мере роста можно разносить по модулям.
- [forms.py](forms.py) — формы админки.
- [singleton_model.py](singleton_model.py) — общие синглтоны и базовые модели (используется в том числе из `main/setup/`).
- [models.py](models.py), [admin.py](admin.py), [templatetags/](templatetags/).

## Шаблоны

- Шаблоны админки — [main/core/admin/views/](../core/admin/views/).
- При сборке фронта может существовать зеркало в `#src/templates/admin/` — синхронизируй осознанно.

## Пакетное удаление (заявки / игры)

- `POST /admin/orders/bulk-delete/` — JSON `{"ids": [<id заявок>]}`; ответ `{"ok": true, "deleted": [...]}`.
- `POST /admin/games/bulk-delete/` — JSON `{"ids": [<id игр>]}`; ответ `{"ok": true, "deleted_game_ids": [...]}`.
- `POST /admin/games/reorder/` — JSON `{"game_id": <id>, "direction": "up"|"down"}` — порядок игр в один день (`display_priority`).
- `POST /admin/games/<pk>/flags/` — JSON `{"toggle": "mark_few_seats"|"reserve_enabled"|"manual_sold_out"}` или явные булевы поля; ответ с актуальными флагами и `badge` для бейджа статуса.
- Список заявок и список игр в админке вызывают эти URL из [main/core/admin/js/app.js](../core/admin/js/app.js) без перезагрузки страницы.

## Скрытие прошедших игр (заявки / игры)

На страницах «Заявки» и «Игры» чекбокс «Скрыть прошедшие» скрывает блоки игр с `data-game-past="1"` (на сервере совпадает с `not game.active()`, как на расписании `/schedule/`). Логика переключения — класс `admin-hide-past-on` на корне `.js-admin-past-filter-root` в [main/core/admin/js/app.js](../core/admin/js/app.js).

## Соглашения

- Новые разделы админки — отдельные `path()` в [urls.py](urls.py), вьюхи в [views.py](views.py) или вынесенных модулях по мере роста.
- Формы — в [forms.py](forms.py); синглтоны — через `SingletonModel` из [singleton_model.py](singleton_model.py).
