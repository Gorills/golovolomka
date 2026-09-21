# Документация проекта «Головоломка»

Карта материалов в `docs/` и связь с кодом.

## Оглавление

| Документ | Назначение |
|----------|------------|
| [PROJECT.md](PROJECT.md) | Стек, структура Django, точки входа, соглашения |
| [Локальные города](development/local-cities.md) | Переключение города на localhost без влияния на прод |
| [ADR рейтинга](adr/0001-rating-integrity-and-delivery.md) | Tenant, ledger/CAS, каталог, outbox и write-only SMS secret |
| [Матрица приёмки рейтинга](rating/acceptance-matrix.md) | Требования v1, статусы и доказательства проверок |
| [Локальный runbook рейтинга](rating/local-runbook.md) | Временная БД, seed, recovery, запуск и безопасная очередь |
| [Корневой README](../README.md) | Исторически шаблон gulp-scss-starter; актуальность для бэкенда ограничена |

При добавлении разделов в `docs/` — обновляйте эту таблицу.
