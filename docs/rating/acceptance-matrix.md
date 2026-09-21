# Матрица приёмки рейтинга v1

Статусы: **passed local** — проверено на frozen local candidate; **planned** —
реализация есть, но полный критерий ещё не выполнен на candidate; **not verified
locally** — зависит от production-среды или реального провайдера.

| Контракт | Статус | Доказательство |
|---|---|---|
| Границы 299.5/300, 699/700, 1499/1500, 9999/10000 | passed local | `test_rank_boundaries_are_inclusive_lower_bounds` |
| `87.5` сохраняется точно; лишняя дробная цифра и отрицательный итог запрещены | passed local | form/domain/DB tests |
| Повтор POST и тот же `operation_id` не применяют дельту дважды | passed local | service idempotency test; HTTP CSRF/state tests |
| Две версии одной статистики не теряют обновления | passed local | CAS conflict и CAS=0 rollback tests; реальный параллелизм SQLite не доказывает |
| Корректировка, событие, достижения и outbox атомарны | passed local | negative-total и catalog CAS rollback tests |
| Прыжок через уровни создаёт одно событие, все первые достижения и одно SMS | passed local | multi-rank service test |
| Повторно достигнутый ранг не создаёт подарок/SMS | passed local | reversal/repeat-rank test |
| Пересчёт каталога не создаёт достижения/SMS | passed local | catalog recalculation test |
| Оператор A не читает и не меняет город B, включая прямые и массовые URL | passed local | HTTP authz negative tests |
| Публичный DTO/HTML не содержит телефон, согласия и внутренний ID | passed local | public HTTP/render test и local startup smoke |
| Поиск, четыре сортировки, направления, пагинация и canonical | passed local | Q3 HTTP/search/sort/pagination regression |
| Изменения выполняются POST+CSRF, чужие объекты дают 404 | passed local | HTTP/security tests |
| Отметка события не меняет SMS или подарок | passed local | Q3 first-writer/ack regression |
| SMS feature-off не вызывает сеть; lease защищает от второго worker | passed local | emergency-stop, stale-lease tests; disabled worker temp-DB smoke |
| Timeout/неоднозначный connection result становится `unknown` без blind retry | passed local | mocked provider test |
| Ручной retry журналируется и закрыт после 3 суток | passed local | domain queue test |
| Ключ отсутствует в HTML, URL и безопасных ошибках | passed local | settings/security tests; значения не выводились в local smoke |
| Порог preview устаревает при изменении каталога/score digest | passed local | stale preview и CAS rollback tests |
| Seed повторяем и создаёт 3 формата × 12 рангов, без команд | passed local | unit test и двойной seed на временной БД |
| Схема поднимается на чистой временной БД; план миграции чист | passed local | temp-DB migrate; `makemigrations --check --dry-run` |
| Пустой рейтинг — штатное состояние | passed local | public empty-city HTTP test |
| Backup/restore сохраняет ledger, achievements и outbox | passed local | temp-DB marker restore; counts 1/1/4/1 и целая FK-цепочка |
| Нет телефона/согласия — delivery `skipped`, event/achievement сохранены | passed local | visible queue-state domain test |
| Пустой SMS-шаблон — видимый `template_missing`, worker не вызывает сеть | passed local | domain + queue tests |
| Emergency stop/disabled сохраняет queue без claim | passed local | mocked test и temp-DB worker smoke |
| Коды SMSPilot 0/1/2/3/-1/-2 отображаются в accepted/delivered/unknown/failed | passed local | mocked provider table test |
| Кириллица считается по 70/67, test mode передаёт `test=1` | passed local | unit/provider tests |
| Bulk retry требует preview, digest и явное подтверждение unknown | passed local | HTTP preview/commit test |
| Web key replace/clear шифрует ciphertext; env source отключает ложное изменение | passed local | HTTP + secret-store tests |
| API/master keys отсутствуют в HTML, URL, errors и обычных логах | passed local | HTTP write-only test; no-value smoke review |
| PNG/JPEG/WEBP ≤2MB и ≤2048px принимаются; неверные/oversize отклоняются | passed local | Q2 upload matrix |
| Имя загруженного logo рандомизировано; при logo обязателен alt | passed local | upload/form test |
| Новый ранг добавляется без кода; duplicate/нестрогий порядок отклоняется | passed local | Q3 catalog/HTTP regression |
| Ack общий для города и не меняет gift/SMS status | passed local | Q3 tenant/conditional-update regression |
| Sitemap содержит абсолютный URL каждого города | passed local | Q2 sitemap regression |
| Canonical исключает search/sort/page; пагинация сохраняет allowlisted query | passed local | Q2/Q3 render regression |
| Stored XSS в team/content остаётся escaped | passed local | public render regression и startup smoke |
| 360/390/1440 responsive layout и drawer keyboard/focus/reduced-motion | passed local (targeted) | Chrome 143/Selenium: F2 public/admin size matrix; B2 drawer at 360/390 and affected admin flows at 1440; visual evidence `/tmp/rating-b2-screens/drawer-360.png`, `/tmp/rating-b2-screens/rank-preview-1440.png`. Полный contrast/CWV-аудит не выполнялся |
| Повторный seed сохраняет редакторские изменения и не ломается на threshold collision | passed local | Q3 regression и temp-DB collision rehearsal |
| Reversal создаётся только явным POST из исходной записи и хранит `reverses_id` | passed local | Q3 domain/HTTP regression |
| Отзыв согласия/смена номера до dispatch запрещает сетевую отправку | passed local | Q3 queue state-machine regression |
| Poll/manual/bulk transitions используют CAS; bulk retry аудитируется | passed local | Q3 queue/HTTP race regression |
| Impact preview показывает город, команду и оба ранга | passed local | Q3 render test и visual Selenium screenshot |
| SMS render/config error оставляет business transaction и видимый failed outbox | passed local | Q3 malformed-template/config regression |
| Повторная активация формата backfill-ит нулевые TeamScore без событий | passed local | Q3 format invariant regression |
| Duplicate-team warning требует явного подтверждения | passed local | Q3 HTTP regression |
| Городские H1/title/description уникальны без двойного суффикса | passed local | Q3 public render regression |
| Test-send доступен только central admin и всегда вызывает provider с `test=1` | passed local | Q3 mocked HTTP/provider regression; live send не выполнялся |
| Team list фильтруется, сортируется и пагинируется в БД до построения DTO | passed local | Q5 query-capture regression: `LIMIT 25 OFFSET 25`, три страницы без потерь/повторов; B3 smoke: 82 команды, 25 загруженных строк, без `TeamScore ... IN (all teams)` |
| «Новые ранги» показывает только повышения, понижения доступны лишь в истории | passed local | Q5 HTTP regression и B3 SSR render с принудительным `direction=decrease` |
| Emergency stop блокирует test-send до обращения к provider | passed local | Q5 mocked HTTP regression: отказ видим оператору, provider не вызван |
| Похожее нормализованное имя команды вызывает предупреждение, но допускает явное подтверждение | passed local | Q5 HTTP regression для точного/похожего/непохожего имени; bounded candidate policy, не hard-unique |
| Superuser создаёт обычного городского оператора без `staff/superuser`; password validation и access создаются атомарно | passed local | `test_superuser_creates_ordinary_operator_and_operator_can_login_to_city_portal`, rollback regression |
| Grant/revoke/regrant сохраняет одну audit access-строку; operator не открывает global admin и provisioning POST | passed local | B7 positive/negative HTTP, CSRF, duplicate, privileged target и inactive-row regression |
| Demo seed создаёт по 30 команд/90 score на существующий город, 12 уровней + no-rank/ties/decimal, историю и три gift status без sending-eligible SMS | passed local (temp DB); active dry-run only | `test_demo_seed`; file-backed rehearsal: first/second run 30/0 created teams, 90/0 adjustments; active Краснодар и Томск dry-run по 30/90, durable counts remained 0 |

Frozen Q5 rating suite: **71/71 passed**. Итоговый Q6 unified gate:
**79/79 passed** (`71 rating + 8 home`), exit 0, 0 skips. Предыдущий
Q4 baseline **75/75 passed** сохранён как историческое доказательство до B3.

Production DB locking, plans запросов, scheduler lifecycle, live SMSPilot/TLS,
balance и callback — **not verified locally** и не входят в локальный v1 запуск.
