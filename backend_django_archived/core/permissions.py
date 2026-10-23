from rest_framework.permissions import BasePermission

ADMIN = "admin"
SUPPORT_ENGINEER = "support_engineer"
USER = "user"


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and getattr(request.user, "role", None) == ADMIN)


class IsSupportStaff(BasePermission):
    """Admins and support engineers — the internal ticket-handling team."""

    def has_permission(self, request, view):
        return bool(
            request.user and getattr(request.user, "role", None) in (ADMIN, SUPPORT_ENGINEER)
        )


class IsTicketOwnerOrSupportStaff(BasePermission):
    """Allows support staff, or the user who raised the ticket."""

    def has_object_permission(self, request, view, obj):
        role = getattr(request.user, "role", None)
        if role in (ADMIN, SUPPORT_ENGINEER):
            return True
        return str(obj.get("created_by")) == str(request.user.id)
