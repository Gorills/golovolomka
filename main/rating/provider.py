import os
from dataclasses import dataclass

import requests

from .models import MessageDelivery
from .secrets import get_sms_api_key


@dataclass
class ProviderResult:
    status: str
    safe_error_code: str = ''
    provider_message_id: str = ''
    provider_status_code: str = ''
    parts: int = None
    cost: object = None
    safe_to_retry: bool = False


class SmsPilotClient:
    endpoint = 'https://smspilot.ru/api.php'

    def __init__(self, api_key=None, timeout=(3.05, 10)):
        self.api_key = api_key if api_key is not None else get_sms_api_key()
        self.timeout = timeout

    @property
    def configured(self):
        return bool(self.api_key)

    def send(self, delivery, *, sender_name='', test_mode=True):
        if not self.configured:
            return ProviderResult(MessageDelivery.Status.FAILED, 'configuration_missing')
        data = {
            'send': delivery.rendered_body,
            'to': delivery.recipient.lstrip('+'),
            'apikey': self.api_key,
            'format': 'json',
        }
        if sender_name:
            data['from'] = sender_name
        if test_mode:
            data['test'] = '1'
        try:
            response = requests.post(self.endpoint, data=data, timeout=self.timeout)
        except requests.ConnectTimeout:
            return ProviderResult(
                MessageDelivery.Status.QUEUED, 'connect_timeout', safe_to_retry=True
            )
        except requests.ReadTimeout:
            return ProviderResult(MessageDelivery.Status.UNKNOWN, 'timeout_unknown')
        except requests.ConnectionError:
            return ProviderResult(MessageDelivery.Status.UNKNOWN, 'connection_unknown')
        except requests.RequestException:
            return ProviderResult(MessageDelivery.Status.UNKNOWN, 'request_unknown')
        if response.status_code == 429:
            return ProviderResult(MessageDelivery.Status.QUEUED, 'rate_limited', safe_to_retry=True)
        if response.status_code >= 500:
            return ProviderResult(MessageDelivery.Status.UNKNOWN, 'provider_unavailable_unknown')
        if response.status_code >= 400:
            return ProviderResult(MessageDelivery.Status.FAILED, 'provider_rejected_http')
        try:
            payload = response.json()
        except ValueError:
            return ProviderResult(MessageDelivery.Status.UNKNOWN, 'invalid_provider_response')
        if payload.get('error'):
            error_text = str(payload.get('error')).lower()
            code = 'insufficient_balance' if 'balance' in error_text else 'provider_rejected'
            return ProviderResult(MessageDelivery.Status.FAILED, code)
        sent = payload.get('send') or payload.get('messages') or []
        first = sent[0] if isinstance(sent, list) and sent else payload
        provider_id = str(first.get('id') or first.get('server_id') or '')
        provider_status = str(first.get('status') if first.get('status') is not None else '0')
        mapped = {
            '0': MessageDelivery.Status.ACCEPTED,
            '1': MessageDelivery.Status.ACCEPTED,
            '2': MessageDelivery.Status.DELIVERED,
            '3': MessageDelivery.Status.UNKNOWN,
            '-1': MessageDelivery.Status.FAILED,
            '-2': MessageDelivery.Status.FAILED,
        }.get(provider_status, MessageDelivery.Status.UNKNOWN)
        return ProviderResult(
            mapped,
            safe_error_code=('provider_failed' if mapped == MessageDelivery.Status.FAILED else ''),
            provider_message_id=provider_id,
            provider_status_code=provider_status,
            parts=first.get('parts'),
            cost=first.get('cost'),
        )

    def poll(self, delivery):
        if not self.configured or not delivery.provider_message_id:
            return ProviderResult(delivery.status, 'status_unavailable')
        try:
            response = requests.post(
                self.endpoint,
                data={
                    'check': delivery.provider_message_id,
                    'apikey': self.api_key,
                    'format': 'json',
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError):
            return ProviderResult(delivery.status, 'status_poll_failed')
        raw = str(payload.get('status', ''))
        mapped = {
            '0': MessageDelivery.Status.ACCEPTED,
            '1': MessageDelivery.Status.ACCEPTED,
            '2': MessageDelivery.Status.DELIVERED,
            '3': MessageDelivery.Status.UNKNOWN,
            '-1': MessageDelivery.Status.FAILED,
            '-2': MessageDelivery.Status.FAILED,
        }.get(raw, MessageDelivery.Status.UNKNOWN)
        return ProviderResult(mapped, provider_status_code=raw)
