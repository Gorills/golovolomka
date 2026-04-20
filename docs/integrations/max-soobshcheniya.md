# Отправка уведомлений в мессенджер MAX

Документ описывает реализацию в проекте **food** и служит инструкцией для переноса в другой проект.

## Назначение

MAX используется как **второй канал** рядом с Telegram: текст обычно собирается под **Telegram Markdown v1** (`*жирный*`), затем для MAX выполняется конвертация жирного и HTTP-запрос к **Platform API MAX**.

Код HTTP и конвертации сосредоточен в `main/orders/max_client.py`.

## Внешний API (как в коде)

| Параметр | Значение |
|----------|----------|
| Базовый URL | `https://platform-api.max.ru` |
| Метод | `POST /messages` |
| Query-параметр | `chat_id=<целое число>` |
| Заголовки | `Authorization: <токен как строка>` (в коде без префикса `Bearer`), `Content-Type: application/json` |
| Тело JSON | `{"text": "...", "format": "markdown"}` — поле `format` передаётся, если включён режим markdown |
| Обрезка текста | до **4000** символов |
| Таймаут HTTP | **30** с |

Официальная документация (ссылка из кода): [POST messages](https://dev.max.ru/docs-api/methods/POST/messages).

При переносе **сверьте** актуальный формат заголовка `Authorization` с документацией MAX — в репозитории токен передаётся «как есть».

## Зависимости

- Python-библиотека **`requests`**.

## Конфигурация в БД (Django-модели)

### Глобальные настройки

`setup.models.BaseSettings` (в коде часто `BaseSettings.objects.get()`):

| Поле | Назначение |
|------|------------|
| `max_access_token` | Токен для API (подпись в админке: «MAX: токен API (Authorization)») |
| `max_chat_id` | Числовой id чата по умолчанию |

### Переопределение по городу (субдомен)

`subdomains.models.Subdomain`:

| Поле | Назначение |
|------|------------|
| `max_chat_id` | Если задан, используется вместо `BaseSettings.max_chat_id` при резолве для заказов с привязкой к субдомену |

### Переопределение для зоны самовывоза / QR-меню

`shop.models.PickupAreas`:

| Поле | Назначение |
|------|------------|
| `max_chat_id` | Если задан, используется вместо дефолта из `BaseSettings` для QR и вызова официанта |

Редактирование полей в админке настраивается в `main/admin/forms.py`.

## Модуль `main/orders/max_client.py`

### `telegram_md_v1_bold_to_max_markdown(text)`

Заменяет в тексте фрагменты вида `*одна строка без звёздочек внутри*` на `**…**`, чтобы приблизить Telegram Markdown v1 к требованиям MAX для **жирного**. Ссылки `[текст](url)` и моноширинный `` `код` `` в типичных случаях не меняются (см. комментарий в коде).

### `resolve_max_chat_id(subdomain=None)`

1. Загружает `BaseSettings`.
2. Если передан объект `subdomain` с заданным `max_chat_id` — возвращает его.
3. Иначе — `BaseSettings.max_chat_id`.

### `resolve_max_chat_id_for_pickup_area(area)`

Аналогично `resolve_max_chat_id`, но приоритет у `area.max_chat_id` (модель зоны самовывоза), затем дефолт из `BaseSettings`.

### `send_max_message(access_token, chat_id, text, silent_fail=True, use_markdown=True)`

Низкоуровневая отправка: проверка токена и `chat_id`, приведение `chat_id` к `int`, сбор JSON, `requests.post`. Ошибки сети и HTTP ≥ 400 логируются (`warning`); при `silent_fail=True` возвращается `False`, при `False` — возможны исключения.

### `send_max_if_configured(chat_id, text_built_for_telegram_md_v1, silent_fail=True)`

1. Читает `max_access_token` из `BaseSettings`.
2. Если токен пустой или `chat_id is None` — возвращает `False` без запроса.
3. Прогоняет текст через `telegram_md_v1_bold_to_max_markdown`.
4. Вызывает `send_max_message` с `use_markdown=True`.

## Точки вызова в приложении

| Файл / функция | Событие | Резолв `chat_id` |
|----------------|---------|------------------|
| `orders.telegram.order_telegram` | Уведомление о новом заказе (тот же текст, что для Telegram) | `resolve_max_chat_id(subdomain)` |
| `orders.views.order_callback` | Форма обратного звонка | `resolve_max_chat_id(None)` — только дефолт из настроек |
| `qr_menu.views.oficiant_call` | Вызов официанта со стола | `resolve_max_chat_id_for_pickup_area(table.area)` |
| `qr_menu.views.order` (POST) | Заказ из QR-меню | `resolve_max_chat_id_for_pickup_area(table.area)` |

В `order_telegram` результат доставки: `send_status = tg_ok or max_ok` — достаточно успеха **любого** из каналов; поле заказа `order_send_status` выставляется по этому флагу.

Telegram и MAX разделены: `send_message` в `orders/telegram.py` только Bot API; MAX только через `max_client`.

## Поведение при ошибках

- По умолчанию `silent_fail=True`: исключения в бизнес-поток не пробрасываются, пишется лог.
- Некорректный `chat_id` (не число) — предупреждение и `False`.

## Чеклист переноса в другой проект

1. Добавить зависимость `requests` (или свой HTTP-клиент с тем же контрактом).
2. Хранить `max_access_token` в секретах (env / зашифрованные настройки), не в коде.
3. Перенести или скопировать логику из `max_client.py` (или вынести в общий пакет).
4. Решить схему маршрутизации `chat_id`: нужны ли уровни «сайт / город / точка», как в этом проекте.
5. Согласовать формат текста: если источник уже в CommonMark с `**`, функция конвертации из Telegram v1 может быть избыточной или её нужно доработать.
6. Сверить с актуальной документацией MAX заголовок `Authorization` и тело запроса.
7. В местах отправки в Telegram дублировать вызов `send_max_if_configured(resolved_chat_id, message)` при необходимости параллельной доставки в MAX.

## Связанные пути в репозитории

| Путь | Роль |
|------|------|
| `main/orders/max_client.py` | HTTP, конвертация, резолв chat_id |
| `main/setup/models.py` | поля `max_access_token`, `max_chat_id` |
| `main/subdomains/models.py` | `max_chat_id` субдомена |
| `main/shop/models.py` | `PickupAreas.max_chat_id` |
| `main/orders/telegram.py` | заказы → MAX |
| `main/orders/views.py` | обратный звонок → MAX |
| `main/qr_menu/views.py` | QR, официант → MAX |
