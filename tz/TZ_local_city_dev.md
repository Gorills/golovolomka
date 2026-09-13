# ТЗ: Локальная работа с городами

Одобрено запросом: удобная локальная разработка по городам без влияния на прод; баннер города не должен перекрывать экраны.

## Проблема

Город на сайте определяется по субдомену (`krasnodar.golovolomka.fun`). На `localhost` / `127.0.0.1` субдомена нет → `city` пустой → попап `city-popup--active` на весь экран, оверлей без закрытия, `body { overflow: hidden }`. Ссылки в попапе ведут на прод (`https://slug.golovolomka.fun`).

## Решение (только loopback-хосты)

Не использовать `DEBUG` как признак (на проде его включает `DynamicDebugMiddleware`).

Признак локали: хост `localhost`, `127.0.0.1` или `*.localhost`.

На локали:

1. Город: `?city=<slug>` → сессия `dev_city` → опционально `DEV_CITY` в `local_settings.py`.
2. `?city=-` сбрасывает выбранный город.
3. Ссылки попапа: текущий путь + `?city=slug` (не прод-домен).
4. Попап не открывается сам; оверлей закрываемый; `overflow: hidden` на body не вешается.

На проде: как сейчас (субдомен, принудительный попап без города). Query `?city=` и сессия игнорируются.

## Файлы

- `main/home/city.py` — резолв города
- `main/home/context_processors.py`, `main/home/views.py`
- `main/core/theme/default/views/components/header.html`, `base.html`
- `main/main/settings.py` — опциональный `DEV_CITY`
- тесты, `docs/development/local-cities.md`
