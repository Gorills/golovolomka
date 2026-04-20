"""
Включает/выключает django.conf.settings.DEBUG по полю BaseSettings.debugging_mode
на время обработки запроса (включая страницу ошибки с трассировкой).

Базовое значение DEBUG по-прежнему задаётся в local_settings; при ошибке чтения БД
оно не меняется. Восстановление — в process_response (после формирования ответа,
в том числе при 500).
"""
import logging

from django.conf import settings
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class DynamicDebugMiddleware(MiddlewareMixin):
    def process_request(self, request):
        self._baseline_debug = settings.DEBUG
        try:
            from setup.models import BaseSettings

            bs = BaseSettings.objects.only('debugging_mode').first()
            if bs is not None:
                settings.DEBUG = bool(bs.debugging_mode)
        except Exception as exc:
            logger.debug(
                'DynamicDebugMiddleware: не удалось прочитать debugging_mode, оставляем DEBUG=%s: %s',
                self._baseline_debug,
                exc,
            )

    def process_response(self, request, response):
        if hasattr(self, '_baseline_debug'):
            settings.DEBUG = self._baseline_debug
        return response
