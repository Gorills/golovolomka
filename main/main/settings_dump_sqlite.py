"""
Временные настройки для `dumpdata` с копии prod SQLite (путь только в env).

  SQLITE_DUMP_PATH=/path/to/db.sqlite3 python manage.py dumpdata ... --settings=main.settings_dump_sqlite
"""
import os
from pathlib import Path

from main.settings import *

_p = os.environ.get("SQLITE_DUMP_PATH")
if not _p:
    raise RuntimeError("Задайте SQLITE_DUMP_PATH — абсолютный путь к файлу db.sqlite3")

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": Path(_p),
    }
}
