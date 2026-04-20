# `main/accounts` — пользователи и allauth

Приложение-обвязка вокруг `django-allauth`.

## Ответственность

URL и вьюхи под префиксом `accounts/` рядом с `allauth.urls` (подключение — в [main/main/urls.py](../main/urls.py)).

## Ключевые файлы

- [urls.py](urls.py), [views.py](views.py), [forms.py](forms.py), [models.py](models.py), [admin.py](admin.py).

## Настройки allauth

- Глобальные параметры (`ACCOUNT_*`, `LOGIN_REDIRECT_URL`, бэкенды) — в [main/main/settings.py](../main/settings.py). При смене поведения проверяй **оба места**: настройки и вьюхи/урлы здесь.

## Границы

- Только пользователь, профиль, вход/регистрация. Не дублируй логику платежей и контентных страниц из `main/home/`.
- Шаблоны страниц входа/регистрации — согласовывай с темой в [main/core/theme/default/](../core/theme/default/).
