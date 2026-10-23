from rest_framework import serializers


class OptionSerializer(serializers.Serializer):
    """Generic {name, is_active} dropdown option — user types, platforms,
    ticket categories."""

    id = serializers.CharField(required=False)
    name = serializers.CharField(max_length=150)
    is_active = serializers.BooleanField(required=False, default=True)
    created_at = serializers.DateTimeField(required=False)
    updated_at = serializers.DateTimeField(required=False)


class PrioritySerializer(serializers.Serializer):
    id = serializers.CharField(required=False)
    name = serializers.CharField(max_length=150)
    level = serializers.IntegerField(help_text="Lower number = more urgent.")
    is_active = serializers.BooleanField(required=False, default=True)
    created_at = serializers.DateTimeField(required=False)
    updated_at = serializers.DateTimeField(required=False)


class WhatsAppTemplateSerializer(serializers.Serializer):
    id = serializers.CharField(required=False)
    key = serializers.CharField(
        max_length=100, help_text="Internal trigger key, e.g. TICKET_CREATED."
    )
    karix_template_id = serializers.CharField(
        max_length=150, required=False, allow_blank=True, allow_null=True
    )
    description = serializers.CharField(required=False, allow_blank=True)
    is_active = serializers.BooleanField(required=False, default=True)
    created_at = serializers.DateTimeField(required=False)
    updated_at = serializers.DateTimeField(required=False)


class SLARuleSerializer(serializers.Serializer):
    id = serializers.CharField(required=False)
    priority = serializers.CharField(max_length=150)
    response_time_minutes = serializers.IntegerField(min_value=1)
    resolution_time_minutes = serializers.IntegerField(min_value=1)
    is_active = serializers.BooleanField(required=False, default=True)
    created_at = serializers.DateTimeField(required=False)
    updated_at = serializers.DateTimeField(required=False)
