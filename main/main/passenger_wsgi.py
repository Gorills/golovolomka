"""
WSGI config for HelloDjango project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/wsgi/
"""

import glob
import os
import sys

# public_html: каталог с main/ и venv/ (не хардкодить домен)
_site_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
site_user_root_dir = os.path.dirname(_site_dir)
sys.path.insert(0, os.path.join(site_user_root_dir, 'main'))
_venv_site = glob.glob(
    os.path.join(site_user_root_dir, 'venv', 'lib', 'python*', 'site-packages')
)
if _venv_site:
    sys.path.insert(1, _venv_site[0])

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'main.settings')

application = get_wsgi_application()