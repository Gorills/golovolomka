"""
Отправка уведомлений в мессенджер MAX (Platform API).
Текст собирается под Telegram Markdown v1; перед отправкой в MAX выполняется конвертация жирного.
См. docs/integrations/max-soobshcheniya.md
"""
import logging
import re

import requests

from setup.models import BaseSettings

logger = logging.getLogger(__name__)

MAX_API_MESSAGES_URL = 'https://platform-api.max.ru/messages'
MAX_TEXT_LIMIT = 4000
HTTP_TIMEOUT = 30


def telegram_md_v1_bold_to_max_markdown(text):
    """`*фрагмент без звёздочек внутри`* → `**фрагмент**` для MAX markdown."""
    if not text:
        return text
    return re.sub(r'\*([^*\n]+)\*', lambda m: f'**{m.group(1)}**', text)


def resolve_max_chat_id(city=None):
    try:
        bs = BaseSettings.objects.get()
    except BaseSettings.DoesNotExist:
        return None
    if city is not None and getattr(city, 'max_chat_id', None) is not None:
        return city.max_chat_id
    return bs.max_chat_id


def send_max_message(access_token, chat_id, text, silent_fail=True, use_markdown=True):
    if not (access_token or '').strip():
        return False
    if chat_id is None:
        return False
    try:
        cid = int(chat_id)
    except (TypeError, ValueError):
        logger.warning('MAX: некорректный chat_id=%r', chat_id)
        return False

    body = {'text': text[:MAX_TEXT_LIMIT]}
    if use_markdown:
        body['format'] = 'markdown'

    try:
        r = requests.post(
            MAX_API_MESSAGES_URL,
            params={'chat_id': cid},
            headers={
                'Authorization': access_token.strip(),
                'Content-Type': 'application/json',
            },
            json=body,
            timeout=HTTP_TIMEOUT,
        )
    except requests.RequestException as e:
        logger.warning('MAX: сетевая ошибка: %s', e)
        if silent_fail:
            return False
        raise

    if r.status_code >= 400:
        logger.warning('MAX: HTTP %s: %s', r.status_code, r.text[:500])
        if silent_fail:
            return False
        r.raise_for_status()

    return True


def send_max_if_configured(chat_id, text_built_for_telegram_md_v1, silent_fail=True):
    try:
        bs = BaseSettings.objects.get()
        token = (bs.max_access_token or '').strip()
    except BaseSettings.DoesNotExist:
        return False

    if not token or chat_id is None:
        return False

    converted = telegram_md_v1_bold_to_max_markdown(text_built_for_telegram_md_v1)
    return send_max_message(token, chat_id, converted, silent_fail=silent_fail, use_markdown=True)
