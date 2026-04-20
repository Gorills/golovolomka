# Документация проекта «Головоломка»

Карта материалов в `docs/` и связь с кодом.

## Оглавление

| Документ | Назначение |
|----------|------------|
| [PROJECT.md](PROJECT.md) | Стек, структура Django, точки входа, соглашения |
| [Корневой README](../README.md) | Исторически шаблон gulp-scss-starter; актуальность для бэкенда ограничена |

Реестр Claude skills (`docs/skills-index.md`): файл пока не создан — при добавлении включить ссылку сюда.

## Правила для AI-ассистентов

### Claude Code

Корневой [CLAUDE.md](../CLAUDE.md) — базовые правила (язык, приоритеты, безопасность, git, legacy-режим, workflow ТЗ и т.д.). Загружается автоматически.

Модульные `CLAUDE.md` подхватываются при работе с файлами внутри директории:

| Область | Путь в репозитории | Правило |
|---------|-------------------|---------|
| Настройки проекта Django | `main/main/` | [main/main/CLAUDE.md](../main/main/CLAUDE.md) |
| Публичный сайт | `main/home/` | [main/home/CLAUDE.md](../main/home/CLAUDE.md) |
| Кастомная админка | `main/admin/` | [main/admin/CLAUDE.md](../main/admin/CLAUDE.md) |
| Аккаунты / allauth | `main/accounts/` | [main/accounts/CLAUDE.md](../main/accounts/CLAUDE.md) |
| Настройки сайта (singleton и др.) | `main/setup/` | [main/setup/CLAUDE.md](../main/setup/CLAUDE.md) |
| Тема, шаблоны, статика сборки | `main/core/` | [main/core/CLAUDE.md](../main/core/CLAUDE.md) |

Первичная настройка проекта — slash-команда `/bootstrap` (см. [.claude/commands/bootstrap.md](../.claude/commands/bootstrap.md)).
Permissions и запреты — [.claude/settings.json](../.claude/settings.json).

### Cursor

Правила для Cursor — в `.cursor/rules/*.mdc` (`globs` и `alwaysApply`).

При добавлении разделов в `docs/` — обновляйте эту таблицу.
