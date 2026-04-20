# `main/setup` — глобальные настройки сайта

Singleton-модели и связанные сущности базовых настроек: контакты, SEO, логотипы, флаги, контентные блоки разных разделов.

## Ключевые файлы

- [models.py](models.py) — singleton и связанные модели.
- [views.py](views.py), [context_processors.py](context_processors.py), [admin.py](admin.py).

## Паттерн

- `SingletonModel` из [main/admin/singleton_model.py](../admin/singleton_model.py) — для записей «одна строка на тип».

## Связь с админкой

- Редактирование обычно идёт через кастомное приложение [main/admin/](../admin/), а **не** через `django.contrib.admin` (который отключён).
- При добавлении полей в модели — обнови формы/вьюхи в `main/admin/` и контекст в `main/home/` при необходимости.

## Миграции

- Стандартный Django, в `setup/migrations/`.
- Если таблицы `setup_*` уже существовали в БД до появления миграций приложения `setup`, после деплоя может понадобиться: `python manage.py migrate setup 0001 --fake`, затем `python manage.py migrate` (колонки Telegram/MAX добавит `0002`).
