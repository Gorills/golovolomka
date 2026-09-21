import base64
import hashlib
import os

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def _fernet():
    try:
        from cryptography.fernet import Fernet, InvalidToken
    except ImportError as exc:
        raise ImproperlyConfigured('cryptography is required for the local SMS secret store') from exc
    master = os.environ.get('RATING_SECRET_ENCRYPTION_KEY') or getattr(
        settings, 'RATING_SECRET_ENCRYPTION_KEY', ''
    )
    if not master:
        raise ImproperlyConfigured('RATING_SECRET_ENCRYPTION_KEY is not configured')
    key = base64.urlsafe_b64encode(hashlib.sha256(master.encode('utf-8')).digest())
    return Fernet(key), InvalidToken


def encrypt_secret(value):
    cipher, _ = _fernet()
    return cipher.encrypt(value.encode('utf-8')).decode('ascii')


def decrypt_secret(value):
    if not value:
        return ''
    cipher, invalid_token = _fernet()
    try:
        return cipher.decrypt(value.encode('ascii')).decode('utf-8')
    except invalid_token as exc:
        raise ImproperlyConfigured('SMS secret cannot be decrypted with the configured key') from exc


def get_sms_api_key():
    env_key = os.environ.get('SMSPILOT_API_KEY', '')
    if env_key:
        return env_key
    from .models import SmsIntegrationSettings

    try:
        stored = SmsIntegrationSettings.get_solo().api_key_ciphertext
    except Exception:
        return ''
    return decrypt_secret(stored) if stored else ''
