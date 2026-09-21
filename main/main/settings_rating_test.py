import os

from .settings import *


_db_path = os.environ.get('RATING_TEST_DB')
if not _db_path:
    raise RuntimeError('RATING_TEST_DB must point to a dedicated temporary SQLite database')

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': _db_path,
        'OPTIONS': {'timeout': 60},
    }
}

DEBUG = False
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
