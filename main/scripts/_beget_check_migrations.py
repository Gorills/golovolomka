#!/usr/bin/env python3
"""Одноразовая проверка БД и правка django_migrations на Beget (не импортировать из кода проекта)."""
import os
import sys

try:
    import pymysql

    pymysql.install_as_MySQLdb()
except ImportError:
    pass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "main.settings")

import django  # noqa: E402

django.setup()

from django.db import connection  # noqa: E402
from django.utils import timezone  # noqa: E402


def main():
    with connection.cursor() as c:
        c.execute("SHOW COLUMNS FROM home_city")
        city_cols = {row[0] for row in c.fetchall()}
        c.execute("SHOW COLUMNS FROM home_gameorder")
        order_cols = {row[0] for row in c.fetchall()}
        c.execute("SHOW COLUMNS FROM home_games")
        games_cols = {row[0] for row in c.fetchall()}

    if "agree_privacy_policy" not in order_cols:
        print("Adding missing home_gameorder.agree_privacy_policy (Django BooleanField → tinyint(1))…")
        with connection.cursor() as c:
            c.execute(
                "ALTER TABLE home_gameorder ADD COLUMN agree_privacy_policy "
                "tinyint(1) NOT NULL DEFAULT 0"
            )
        order_cols.add("agree_privacy_policy")

    need_0014 = {
        "home_city.max_chat_id": "max_chat_id" in city_cols,
        "home_gameorder.agree_privacy_policy": "agree_privacy_policy" in order_cols,
        "home_gameorder.first_time": "first_time" in order_cols,
        "home_games.display_priority": "display_priority" in games_cols,
    }
    print("Columns from 0014_auto:", need_0014)
    if not all(need_0014.values()):
        print("ERROR: DB still missing columns from 0014 — stop.", file=sys.stderr)
        sys.exit(2)

    with connection.cursor() as c:
        c.execute(
            "SELECT COUNT(*) FROM django_migrations WHERE app=%s AND name=%s",
            ["home", "0014_auto_20260424_0600"],
        )
        if c.fetchone()[0]:
            print("0014_auto already in django_migrations — nothing to insert.")
            return
        c.execute(
            "INSERT INTO django_migrations (app, name, applied) VALUES (%s, %s, %s)",
            ["home", "0014_auto_20260424_0600", timezone.now()],
        )
    print("Inserted applied row for home.0014_auto_20260424_0600 (schema matches migration).")


if __name__ == "__main__":
    main()
