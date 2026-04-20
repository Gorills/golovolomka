# `main/main` — конфигурация проекта Django

Пакет настроек всего проекта. Правки здесь влияют на все приложения.

## Ключевые файлы

- [settings.py](settings.py) — `INSTALLED_APPS`, allauth, CKEditor, WhiteNoise.
- [urls.py](urls.py) — корневая маршрутизация; порядок `include()` важен: `home.urls` подключается **последним** из-за catch-all `<slug:slug>/`; медиа/статика через `static()`.
- [local_settings.py](local_settings.py) / [local_settings_copy.py](local_settings_copy.py) — секреты и прод-настройки. В индекс не попадают.
- [passenger_wsgi.py](passenger_wsgi.py) — WSGI для хостинга. Менять только осознанно при деплое.
- [my_whitenoise.py](my_whitenoise.py), [static_setup.py](static_setup.py) — кастомные модули статики.
- [middleware.py](middleware.py) — `DynamicDebugMiddleware`: на время запроса выставляет `settings.DEBUG` из `setup.BaseSettings.debugging_mode` (базовое значение — из `local_settings`), восстанавливает в `process_response`.

## Контракты

- Не создавай циклические импорты из `home`/`admin` в `settings.py`.
- Зарезервированное имя `admin` в `INSTALLED_APPS` занято **кастомным** приложением `main/admin/`; стандартный `django.contrib.admin` отключён.
- `handler404` указывает на `home.views.page_not_found_view` — при переименовании вьюхи синхронизируй.
- Новые публичные маршруты, которые могут конфликтовать со slug страниц, регистрируй в `home/urls.py` **выше** универсального `'<slug:slug>/'`.
