from rest_framework import serializers


class NotificationLogSerializer(serializers.Serializer):
    id = serializers.CharField()
    ticket_id = serializers.CharField(allow_null=True)
    template_key = serializers.CharField()
    to_phone = serializers.CharField(allow_null=True)
    status = serializers.CharField()
    karix_message_id = serializers.CharField(allow_null=True, required=False)
    error = serializers.CharField(allow_null=True, required=False)
    created_at = serializers.DateTimeField()


class KarixWebhookSerializer(serializers.Serializer):
    """Inbound WhatsApp reply from Karix. Field names are a best-effort
    placeholder — adjust to match Karix's actual webhook payload once shared."""

    source = serializers.CharField(help_text="Sender's WhatsApp number (the user who replied).")
    text = serializers.CharField(required=False, allow_blank=True)
