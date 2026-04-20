# `main/home` — публичное приложение

Публичные страницы сайта: CMS-страницы по slug, sitemap, приём заявок, игры, интеграции.

## Ключевые файлы

- [views.py](views.py), [urls.py](urls.py) — публичные вьюхи и маршруты.
- [models.py](models.py) — модели контента и заявок.
- [sitemaps.py](sitemaps.py) — sitemap.
- [context_processors.py](context_processors.py) — глобальный контекст для шаблонов.
- [telegram.py](telegram.py) — отправка в Telegram (токен и чат по умолчанию из `setup.BaseSettings`).
- [max_client.py](max_client.py) — отправка тех же текстов в MAX (Platform API), см. `docs/integrations/max-soobshcheniya.md`.
- [forms.py](forms.py), [templatetags/](templatetags/), [migrations/](migrations/).

## Маршрутизация

- В [urls.py](urls.py) есть catch-all `'<slug:slug>/'` для деталей страниц. **Новые фиксированные пути добавляй выше этой записи**, иначе их перехватит slug.
- Глобальный `handler404` в корневом `main/main/urls.py` ссылается на `home.views.page_not_found_view`.

## Шаблоны

- HTML для темы по умолчанию — в [main/core/theme/default/views/](../core/theme/default/views/). При смене путей шаблонов проверяй `TEMPLATES` в `main/main/settings.py` и вызовы `render()` в этом приложении.

## Границы

- Бизнес-логика админки — в `main/admin/`, глобальные настройки — в `main/setup/`. Не дублируй оттуда логику без явной необходимости.
- Логика пользователей/allauth — в `main/accounts/`.
