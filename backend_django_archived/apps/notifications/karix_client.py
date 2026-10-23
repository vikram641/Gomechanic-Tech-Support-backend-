"""Karix (Airtel IQ CPaaS) WhatsApp Business API integration.

The exact request/response shape below is a best-effort placeholder based on
Karix's typical WhatsApp template-message contract. Once real API
credentials and template IDs are shared, only `_build_payload` and the
response-field names read in `send_template_message` should need updating —
everything else (trigger points, logging, graceful degradation) stays as is.
"""

import requests
from django.conf import settings

from apps.configuration.repository import get_template_by_key
from apps.notifications.repository import log_notification


class KarixWhatsAppService:
    def __init__(self):
        self.api_key = settings.KARIX_API_KEY
        self.source = settings.KARIX_SOURCE_ADDRESS
        self.base_url = settings.KARIX_API_BASE_URL.rstrip("/")

    def is_configured(self):
        return bool(self.api_key and self.source)

    def _build_payload(self, to_phone, karix_template_id, params):
        return {
            "source": self.source,
            "destination": to_phone,
            "channel": "whatsapp",
            "message": {
                "type": "template",
                "template": {
                    "templateId": karix_template_id,
                    "params": params or [],
                },
            },
        }

    def send_template_message(self, *, to_phone, template_key, ticket=None, params=None):
        ticket_id = ticket.get("ticket_id") if ticket else None
        template = get_template_by_key(template_key)

        if not template or not template.get("is_active", True):
            return log_notification(
                ticket_id=ticket_id, template_key=template_key, to_phone=to_phone,
                payload=None, status="SKIPPED_NO_TEMPLATE",
            )

        karix_template_id = template.get("karix_template_id")
        if not self.is_configured() or not karix_template_id:
            return log_notification(
                ticket_id=ticket_id, template_key=template_key, to_phone=to_phone,
                payload=None, status="SKIPPED_NOT_CONFIGURED",
            )

        payload = self._build_payload(to_phone, karix_template_id, params)
        try:
            response = requests.post(
                f"{self.base_url}/whatsapp/v1/message",
                json=payload,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=10,
            )
            response.raise_for_status()
            body = response.json()
            return log_notification(
                ticket_id=ticket_id, template_key=template_key, to_phone=to_phone,
                payload=payload, status="SENT",
                karix_message_id=body.get("messageId") or body.get("id"),
            )
        except requests.RequestException as exc:
            return log_notification(
                ticket_id=ticket_id, template_key=template_key, to_phone=to_phone,
                payload=payload, status="FAILED", error=str(exc),
            )
