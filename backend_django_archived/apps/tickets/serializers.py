from rest_framework import serializers

from apps.tickets import constants


class AttachmentSerializer(serializers.Serializer):
    filename = serializers.CharField()
    url = serializers.CharField()
    content_type = serializers.CharField(required=False, allow_blank=True)
    uploaded_at = serializers.DateTimeField()


class ActivityLogEntrySerializer(serializers.Serializer):
    actor_id = serializers.CharField(allow_null=True)
    actor_name = serializers.CharField(allow_null=True)
    action = serializers.CharField()
    from_status = serializers.CharField(allow_null=True)
    to_status = serializers.CharField(allow_null=True)
    note = serializers.CharField(allow_null=True, required=False)
    created_at = serializers.DateTimeField()


class NoteSerializer(serializers.Serializer):
    author_id = serializers.CharField()
    author_name = serializers.CharField()
    note = serializers.CharField()
    created_at = serializers.DateTimeField()


class TicketCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200)
    description = serializers.CharField()
    user_type = serializers.CharField(max_length=150)
    platform = serializers.CharField(max_length=150)
    category = serializers.CharField(max_length=150, required=False, allow_null=True)
    priority = serializers.CharField(max_length=150, required=False, allow_null=True)
    login_credentials = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    def validate_user_type(self, value):
        from apps.configuration.repository import USER_TYPES, is_active_option

        if not is_active_option(USER_TYPES, value):
            raise serializers.ValidationError("Unknown or inactive user type.")
        return value

    def validate_platform(self, value):
        from apps.configuration.repository import PLATFORMS, is_active_option

        if not is_active_option(PLATFORMS, value):
            raise serializers.ValidationError("Unknown or inactive platform.")
        return value

    def validate_category(self, value):
        from apps.configuration.repository import TICKET_CATEGORIES, is_active_option

        if value and not is_active_option(TICKET_CATEGORIES, value):
            raise serializers.ValidationError("Unknown or inactive ticket category.")
        return value

    def validate_priority(self, value):
        from apps.configuration.repository import TICKET_PRIORITIES, is_active_option

        if value and not is_active_option(TICKET_PRIORITIES, value):
            raise serializers.ValidationError("Unknown or inactive priority.")
        return value


class PublicTicketCreateSerializer(TicketCreateSerializer):
    """Same as TicketCreateSerializer, plus the contact details needed to
    identify a guest who isn't logged in (no account to pull name/email/phone
    from). Used by the no-login public submission form."""

    name = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=20)


class TicketListItemSerializer(serializers.Serializer):
    id = serializers.CharField()
    ticket_id = serializers.CharField()
    title = serializers.CharField()
    user_type = serializers.CharField()
    platform = serializers.CharField()
    category = serializers.CharField(allow_null=True)
    priority = serializers.CharField()
    status = serializers.CharField()
    assigned_to_snapshot = serializers.DictField(allow_null=True, required=False)
    created_by_snapshot = serializers.DictField(allow_null=True, required=False)
    reopened_count = serializers.IntegerField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class TicketDetailSerializer(TicketListItemSerializer):
    description = serializers.CharField()
    login_credentials = serializers.CharField(allow_null=True, required=False)
    attachments = AttachmentSerializer(many=True)
    created_by = serializers.CharField(allow_null=True)
    assigned_to = serializers.CharField(allow_null=True)
    internal_notes = NoteSerializer(many=True)
    csat_status = serializers.CharField(allow_null=True)
    first_response_at = serializers.DateTimeField(allow_null=True)
    resolved_at = serializers.DateTimeField(allow_null=True)
    closed_at = serializers.DateTimeField(allow_null=True)


class AssignSerializer(serializers.Serializer):
    engineer_id = serializers.CharField()

    def validate_engineer_id(self, value):
        from apps.accounts.repository import find_user_by_id

        engineer = find_user_by_id(value)
        if not engineer:
            raise serializers.ValidationError("Engineer not found.")
        if engineer.get("role") not in ("admin", "support_engineer"):
            raise serializers.ValidationError("This user is not a support engineer or admin.")
        if not engineer.get("is_active", True):
            raise serializers.ValidationError("This engineer's account is deactivated.")
        return value


class StatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=constants.ALL_STATUSES)
    note = serializers.CharField(required=False, allow_blank=True)


class NoteCreateSerializer(serializers.Serializer):
    note = serializers.CharField()


class CSATResponseSerializer(serializers.Serializer):
    satisfied = serializers.BooleanField()
