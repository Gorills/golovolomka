"""
Настройки для `manage.py migrate` с локальной машины на MySQL Beget через SSH-туннель.

Пароль задаётся только в окружении, в репозитории не хранится:
  export BEGET_MYSQL_PASSWORD='...'
Опционально: BEGET_MYSQL_NAME, BEGET_MYSQL_USER, BEGET_MYSQL_HOST, BEGET_MYSQL_PORT.
"""
import os

try:
    import pymysql
except ImportError:
    pymysql = None
if pymysql is not None:
    pymysql.install_as_MySQLdb()

from main.settings import *

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.environ.get("BEGET_MYSQL_NAME", "maksudaq_db"),
        "USER": os.environ.get("BEGET_MYSQL_USER", "maksudaq_db"),
        "PASSWORD": os.environ["BEGET_MYSQL_PASSWORD"],
        "HOST": os.environ.get("BEGET_MYSQL_HOST", "127.0.0.1"),
        "PORT": os.environ.get("BEGET_MYSQL_PORT", "3306"),
        "OPTIONS": {"charset": "utf8mb4"},
    }
}
