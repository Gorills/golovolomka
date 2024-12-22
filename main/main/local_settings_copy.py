from main.settings import BASE_DIR
from main.settings import *
import os





# STATIC_URL = 'core/'

# STATIC_ROOT = '/home/a/avroraweb/oasis.tomsk.ru/public_html/main/core/'

STATIC_URL = 'core/'
STATIC_ROOT = '/home/a/avroraweb/oasis.tomsk.ru/public_html/main/core'

# STATICFILES_DIRS = (
#     os.path.join(BASE_DIR, "core"),
#     '/home/a/avroraweb/oasis.tomsk.ru/public_html/main/core/',
# )


STATICFILES_DIRS = [
    BASE_DIR / "core",
   '/home/a/avroraweb/oasis.tomsk.ru/public_html/main/core/',
]



MEDIA_URL = 'main/media/'
MEDIA_ROOT = '/home/a/avroraweb/oasis.tomsk.ru/public_html/main/media/'





DEBUG = True
ALLOWED_HOSTS = ['oasis.avroraweb.beget.tech']


RESET_FILE = '/home/a/avroraweb/oasis.tomsk.ru/public_html/main/main/tmp/restart.txt'



DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql', 
        'NAME': 'avroraweb_oasis',
        'USER': 'avroraweb_oasis',
        'PASSWORD': 'Ie51587v!',
        'HOST': 'localhost',
        
    }
}



LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': 'debug.log',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}