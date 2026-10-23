from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.configuration import repository
from apps.configuration.serializers import (
    OptionSerializer,
    PrioritySerializer,
    SLARuleSerializer,
    WhatsAppTemplateSerializer,
)
from core.permissions import IsAdmin


class DropdownListCreateView(APIView):
    """Generic list/create for a single configuration collection.

    Reads are public — no auth required. This is dropdown reference data
    (user types, platforms, etc.), not sensitive, and the public ticket-raiser
    registration form needs to read `user-types` before the visitor has an
    account/token. Writes are admin-only, matching the FRD's 'manage from
    admin panel, no code changes' requirement.
    """

    collection_name = None
    serializer_class = OptionSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAdmin()]
        return [AllowAny()]

    def get(self, request):
        active_only = request.query_params.get("active_only", "true").lower() != "false"
        options = repository.list_options(self.collection_name, active_only=active_only)
        data = self.serializer_class(
            [repository.to_public(o) for o in options], many=True
        ).data
        return Response(data)

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            doc = repository.create_option(self.collection_name, serializer.validated_data)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(self.serializer_class(repository.to_public(doc)).data, status=201)


class DropdownDetailView(APIView):
    collection_name = None
    serializer_class = OptionSerializer

    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAdmin()]

    def get(self, request, option_id):
        option = repository.get_option(self.collection_name, option_id)
        if not option:
            return Response({"detail": "Not found."}, status=404)
        return Response(self.serializer_class(repository.to_public(option)).data)

    def patch(self, request, option_id):
        if not repository.get_option(self.collection_name, option_id):
            return Response({"detail": "Not found."}, status=404)
        serializer = self.serializer_class(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated = repository.update_option(self.collection_name, option_id, serializer.validated_data)
        return Response(self.serializer_class(repository.to_public(updated)).data)

    def delete(self, request, option_id):
        if not repository.get_option(self.collection_name, option_id):
            return Response({"detail": "Not found."}, status=404)
        repository.delete_option(self.collection_name, option_id)
        return Response(status=204)


# --- one list/detail pair per configurable dropdown type -------------------


class UserTypeListCreateView(DropdownListCreateView):
    collection_name = repository.USER_TYPES


class UserTypeDetailView(DropdownDetailView):
    collection_name = repository.USER_TYPES


class PlatformListCreateView(DropdownListCreateView):
    collection_name = repository.PLATFORMS


class PlatformDetailView(DropdownDetailView):
    collection_name = repository.PLATFORMS


class TicketCategoryListCreateView(DropdownListCreateView):
    collection_name = repository.TICKET_CATEGORIES


class TicketCategoryDetailView(DropdownDetailView):
    collection_name = repository.TICKET_CATEGORIES


class TicketPriorityListCreateView(DropdownListCreateView):
    collection_name = repository.TICKET_PRIORITIES
    serializer_class = PrioritySerializer


class TicketPriorityDetailView(DropdownDetailView):
    collection_name = repository.TICKET_PRIORITIES
    serializer_class = PrioritySerializer


class WhatsAppTemplateListCreateView(DropdownListCreateView):
    collection_name = repository.WHATSAPP_TEMPLATES
    serializer_class = WhatsAppTemplateSerializer


class WhatsAppTemplateDetailView(DropdownDetailView):
    collection_name = repository.WHATSAPP_TEMPLATES
    serializer_class = WhatsAppTemplateSerializer


class SLARuleListCreateView(DropdownListCreateView):
    collection_name = repository.SLA_RULES
    serializer_class = SLARuleSerializer


class SLARuleDetailView(DropdownDetailView):
    collection_name = repository.SLA_RULES
    serializer_class = SLARuleSerializer
