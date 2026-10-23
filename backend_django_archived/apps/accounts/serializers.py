from rest_framework import serializers

from apps.accounts.repository import ROLES


class RegisterSerializer(serializers.Serializer):
    """Public self-registration — always creates a ticket-raising 'user'."""

    name = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    password = serializers.CharField(min_length=8, write_only=True)
    user_type = serializers.CharField(max_length=100)

    def validate_user_type(self, value):
        from apps.configuration.repository import is_active_option

        if not is_active_option("user_types", value):
            raise serializers.ValidationError(
                "Unknown or inactive user type. Check /api/config/user-types/ for valid values."
            )
        return value


class AdminUserCreateSerializer(serializers.Serializer):
    """Used by admins to create support engineers/admins/users directly."""

    name = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    password = serializers.CharField(min_length=8, write_only=True)
    role = serializers.ChoiceField(choices=ROLES, default="support_engineer")
    user_type = serializers.CharField(max_length=100, required=False, allow_null=True)

    def validate(self, attrs):
        if attrs.get("role") == "user" and not attrs.get("user_type"):
            raise serializers.ValidationError({"user_type": "Required when role is 'user'."})
        return attrs


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class RefreshSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class UserSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    email = serializers.EmailField()
    phone = serializers.CharField(allow_null=True, required=False)
    role = serializers.CharField()
    user_type = serializers.CharField(allow_null=True, required=False)
    is_active = serializers.BooleanField()
    created_at = serializers.DateTimeField()


class UserUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150, required=False)
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    is_active = serializers.BooleanField(required=False)
    password = serializers.CharField(min_length=8, required=False, write_only=True)
