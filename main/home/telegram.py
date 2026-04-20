import logging
import re

import telepot

from setup.models import BaseSettings

logger = logging.getLogger(__name__)


def _get_bot_token():
    try:
        return (BaseSettings.objects.get().telegram_bot_token or '').strip()
    except BaseSettings.DoesNotExist:
        return ''


def _get_default_telegram_group():
    try:
        return (BaseSettings.objects.get().telegram_default_group or '').strip()
    except BaseSettings.DoesNotExist:
        return ''


def send_message(message, telegram_group=None):
    token = _get_bot_token()
    if not token:
        logger.warning('Telegram: не задан токен бота в общих настройках')
        return False

    if telegram_group is None:
        telegram_group = _get_default_telegram_group()
    if not telegram_group:
        logger.warning('Telegram: не задан чат по умолчанию и не передан telegram_group')
        return False

    telegram_bot = telepot.Bot(token)
    telegram_bot.sendMessage(telegram_group, message, parse_mode='Markdown')
    return True
