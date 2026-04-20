# Проект: Головоломка (golovolomka)

## Стек

- **Python / Django** 3.2 (`requirements.txt` в корне репозитория).
- **БД**: в репозитории зачастую SQLite (`db.sqlite3` в `.gitignore`); `mysqlclient` в requirements закомментирован.
- **Аутентификация**: `django-allauth`.
- **Контент**: CKEditor + загрузчик, `sorl-thumbnail`, `django-cleanup`.
- **Платежи / внешние**: `yookassa`, `telepot`, `requests`, DRF (при необходимости API).
- **Статика**: WhiteNoise (см. импорты в `main/main/settings.py`), кастомные модули whitenoise рядом с настройками.
- **Фронт**: шаблоны и собранные CSS/JS в `main/core/`; в корне есть каталог `#src/` (scss/html зеркала) — уточняйте у команды, какая копия считается источником при сборке.

## Структура

- **`main/`** — корень Django-проекта (`manage.py`).
- **`main/main/`** — пакет настроек: `settings.py`, `urls.py`, WSGI/Passenger.
- **`main/home/`** — публичные страницы, CMS-страницы по slug, sitemap, обработчики заявок/игр. Уведомления о заявках: `telegram.py` (токен и чат по умолчанию в `setup.BaseSettings`), дублирование в MAX — `max_client.py` (см. `docs/integrations/max-soobshcheniya.md`).
- **`main/admin/`** — **не** `django.contrib.admin`: отдельное приложение кастомной админки по префиксу `/admin/`.
- **`main/accounts/`** — маршруты и логика вокруг пользователей и allauth.
- **`main/setup/`** — модели глобальных/контентных настроек (singleton и связанные сущности). В `BaseSettings` хранятся токен Telegram-бота, чат по умолчанию, токен и чат MAX для уведомлений.
- **`main/core/`** — тема по умолчанию: HTML-шаблоны, JS, скомпилированный CSS, изображения; отдельно вложенные шаблоны **админки** в `core/admin/`.

Корневой **`README.md`** описывает gulp-scss-starter и может не отражать текущий процесс деплоя сайта.

## Точки входа

- Запуск: `python main/manage.py` (из корня или из `main/` — по принятой у команде привычке).
- URL: `main/main/urls.py` — подключает `admin.urls`, `accounts`, `ckeditor_uploader`, затем `home.urls` (последним из-за catch-all slug).
- Локальные секреты и прод-настройки: `local_settings.py`, ключи — вне репозитория (см. `.gitignore`).

## Соглашения

- Имена приложений в `INSTALLED_APPS`: зарезервированное имя `admin` занято **кастомным** приложением; стандартный `django.contrib.admin` отключён.
- Обработчик 404: `handler404` указывает на `home.views.page_not_found_view`.
- Новые публичные маршруты без конфликта со slug страниц — регистрировать **выше** универсального `'<slug:slug>/'` в `home/urls.py`.

## Ограничения

- Секреты и пароли БД не хранить в `settings.py`; для локали использовать `local_settings.py`.
- Не полагаться на корневой README как на единственный источник правды по деплою.
