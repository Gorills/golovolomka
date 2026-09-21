# Локальный запуск рейтинга

Реальная отправка SMS по умолчанию выключена. Не задавайте production API-ключ
для локальных проверок.

Для теста write-only web workflow задайте случайный локальный
`RATING_SECRET_ENCRYPTION_KEY`. Если активен `SMSPILOT_API_KEY`, web-замена и
удаление отключены: environment имеет приоритет. Значения ключей никогда не
печатайте в командной строке, логах или отчёте.

После локального входа суперпользователем откройте `/rating-admin/integration/`.
Поле нового ключа всегда пустое. При source `environment` кнопки замены/удаления
не должны обещать изменение активного ключа. При source `encrypted_store`
непустое поле заменяет ciphertext, отдельный checkbox удаляет его; повторный GET
показывает только `key configured`, source и доступность изменения. Для этой
проверки используйте фиктивное значение, оставьте отправку выключенной и после
проверки явно очистите ciphertext.

## Обычные проверки

Из корня репозитория:

```bash
.venv/bin/python main/manage.py check
.venv/bin/python main/manage.py makemigrations --check --dry-run
.venv/bin/python main/manage.py test home rating
.venv/bin/python main/manage.py migrate --plan
```

## Чистая временная база

Создайте временный каталог и передайте путь через `RATING_TEST_DB`; специальный
settings-модуль заменит только имя SQLite базы. Не указывайте `main/db.sqlite3`.

```bash
tmpdir="$(mktemp -d)"
RATING_TEST_DB="$tmpdir/rating.sqlite3" \
  .venv/bin/python main/manage.py migrate --settings=main.settings_rating_test
RATING_TEST_DB="$tmpdir/rating.sqlite3" \
  .venv/bin/python main/manage.py rating_seed --settings=main.settings_rating_test
```

Повтор `rating_seed` сохраняет все существующие названия, пороги, описания,
подарки, порядок и active-state. Он создаёт только отсутствующие начальные
форматы/уровни. Если отсутствующий уровень конфликтует по порогу с существующим
рангом, команда выводит `Skipped missing seed rank` и не меняет каталог; такую
коллизию исправляйте через preview каталога. Для проверки восстановления
копируйте только временную БД, добавьте тестовую запись, восстановите копию и
повторите `check`/`rating_seed`. Удаление временного каталога допустимо только
после проверки его точного пути.

## Локальные демонстрационные команды

`rating_demo_seed` предназначена только для существующего города в ожидаемой
локальной SQLite базе. Команда требует ID активного суперпользователя и
отказывается работать, если включена отправка SMS, выключен emergency stop,
выключен test mode, настроен API-ключ или уже есть delivery в состоянии
`queued`, `processing` либо `accepted`.

Сначала остановите локальный web/worker, проверьте БД и сделайте online backup:

```bash
sqlite3 main/db.sqlite3 'PRAGMA quick_check;'
sqlite3 main/db.sqlite3 ".backup '/tmp/golovolomka-rating-before-demo.sqlite3'"
sqlite3 /tmp/golovolomka-rating-before-demo.sqlite3 'PRAGMA quick_check;'
```

Затем выполните rollback-only прогон, подставив существующий slug и ID
суперпользователя:

```bash
.venv/bin/python main/manage.py rating_demo_seed \
  --city krasnodar --actor-id 1 --dry-run
.venv/bin/python main/manage.py rating_demo_seed \
  --city tomsk --actor-id 1 --dry-run
```

Ожидаемый план для пустого города: 30 явно помеченных demo-команд, 90 score,
все 12 уровней, строки без ранга, дробные баллы, ничьи и разные числа игр.
Контакты остаются пустыми, `sms_allowed=False`, а создаваемые delivery имеют
только безопасный статус `skipped`. Dry-run полностью откатывает записи.

Запускайте только перечисленные существующие города; команда никогда не создаёт
город автоматически. После независимой проверки исходников снимите свежий backup
и уберите `--dry-run` в каждой команде. Сразу повторите обе команды: второй запуск должен показать
`created_teams=0 created_adjustments=0`. Команда не меняет города, пользователей,
форматы, ранги, тексты, подарки или media. При совпадении имени/marker либо
неполной чужой статистике вся транзакция откатывается.

Для rollback остановите процессы и восстановите SQLite backup целиком в новый
файл, проверьте `PRAGMA quick_check`, затем атомарно замените рабочий файл по
обычной процедуре эксплуатации. Не удаляйте demo-строки каскадными SQL-командами:
ledger использует защищённые внешние ключи, а backup является согласованной
точкой восстановления.

До восстановления остановите локальный сервер и worker. В непустой проверочной
базе сохраните backup, измените только рабочую копию, затем восстановите backup в
новый файл. После восстановления проверьте отсутствие marker-записи, количества
`ScoreAdjustment`, `RankChangeEvent`, `TeamRankAchievement`, `MessageDelivery` и
ссылку `MessageDelivery → RankChangeEvent → TeamScore`. Не используйте этот
rehearsal для `main/db.sqlite3`.

Для production-like локального старта с `DEBUG=False`:

```bash
RATING_TEST_DB="$tmpdir/rating.sqlite3" \
  .venv/bin/python main/manage.py runserver 127.0.0.1:8877 --noreload \
  --settings=main.settings_rating_test
```

Откройте `/rating/?city=<slug>` на `localhost:8877` или используйте
`<slug>.localhost:8877/rating/`. Для кабинетных экранов нужен локальный
superuser и явный `CityRatingAccess` для обычного оператора.

## Очередь

`process_rating_sms` ничего не отправляет, пока в `/rating-admin/integration/`
выключена отправка или включён emergency stop. Строки `queued` при этом остаются
без lease и попытки. В тестах провайдер заменяется mock-адаптером. Для реальной
интеграции потребуются отдельное разрешение, API-ключ, утверждённый шаблон,
проверенный баланс и внешний scheduler.

Локальная безопасная проверка:

```bash
RATING_TEST_DB="$tmpdir/rating.sqlite3" \
  .venv/bin/python main/manage.py process_rating_sms \
  --settings=main.settings_rating_test
```

При выключенной отправке результат должен быть `processed=0 paused=True`; сеть
не вызывается, а очередь не меняется.

Central admin может сохранить отдельный тестовый номер и нажать «Проверить
тестовую отправку». Этот POST всегда передаёт провайдеру `test=1`, независимо от
обычного переключателя режима, и показывает только безопасный status/error code.
В автоматических проверках клиент провайдера обязан быть mock; live test-send
требует отдельного разрешения и в локальной приёмке не выполняется.

Перед фактическим dispatch worker повторно проверяет текущие согласие и номер.
Отзыв согласия даёт `consent_revoked`, пустой номер — `missing_phone_current`,
смена номера — `recipient_changed`; во всех трёх случаях сеть не вызывается.
Смена номера при включённых SMS требует новой даты фиксации согласия, а при
выключенных SMS очищает старые consent metadata.

## Непроверяемое локально

SQLite не реализует `SELECT FOR UPDATE`; production-конкуренция, планы запросов,
cron/Passenger lifecycle, TLS и SMSPilot проверяются отдельно на выбранном
окружении. `cryptography==47.0.0` работает на текущем Python 3.8, но сообщает,
что следующая версия прекратит его поддержку; обновление Python нужно планировать
до следующего изменения pin.
