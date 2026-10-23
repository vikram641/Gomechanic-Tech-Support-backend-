import uuid
from types import SimpleNamespace

from dateutil import parser as date_parser

from django.core.files.storage import default_storage
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.tickets import constants, repository
from apps.tickets.serializers import (
    AssignSerializer,
    CSATResponseSerializer,
    NoteCreateSerializer,
    PublicTicketCreateSerializer,
    StatusUpdateSerializer,
    TicketCreateSerializer,
    TicketDetailSerializer,
    TicketListItemSerializer,
)
from core.pagination import DefaultPagination
from core.permissions import IsSupportStaff, IsTicketOwnerOrSupportStaff
from core.utils import now, to_object_id


def _save_attachments(files, ticket_id):
    saved = []
    for f in files:
        ext = f.name.rsplit(".", 1)[-1] if "." in f.name else ""
        key = f"uploads/tickets/{ticket_id}/{uuid.uuid4().hex}" + (f".{ext}" if ext else "")
        path = default_storage.save(key, f)
        saved.append(
            {
                "filename": f.name,
                "url": default_storage.url(path),
                "content_type": getattr(f, "content_type", ""),
                "uploaded_at": now(),
            }
        )
    return saved


def _parse_date(value):
    if not value:
        return None
    try:
        return date_parser.parse(value)
    except (ValueError, OverflowError):
        return None


def _notify(template_key, ticket, extra_params=None):
    """Best-effort WhatsApp notification — never lets a delivery failure
    block the ticket workflow itself."""
    from apps.notifications.karix_client import KarixWhatsAppService

    phone = (ticket.get("created_by_snapshot") or {}).get("phone")
    if not phone:
        return
    try:
        KarixWhatsAppService().send_template_message(
            to_phone=phone,
            template_key=template_key,
            ticket=ticket,
            params=extra_params or {},
        )
    except Exception:
        pass


class TicketListCreateView(APIView):
    def get(self, request):
        is_end_user = getattr(request.user, "role", None) == "user"
        created_by = request.user.id if is_end_user else request.query_params.get("created_by")

        items, total, page, page_size = repository.list_tickets(
            status=request.query_params.get("status"),
            user_type=request.query_params.get("user_type"),
            platform=request.query_params.get("platform"),
            priority=request.query_params.get("priority"),
            assigned_to=request.query_params.get("assigned_to"),
            created_by=created_by,
            date_from=_parse_date(request.query_params.get("date_from")),
            date_to=_parse_date(request.query_params.get("date_to")),
            search=request.query_params.get("search"),
            request=request,
        )
        paginator = DefaultPagination()
        page_items = paginator.paginate_list(request, items, total)
        data = TicketListItemSerializer(
            [repository.to_public(t) for t in page_items], many=True
        ).data
        return paginator.get_paginated_response(data)

    def post(self, request):
        serializer = TicketCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        ticket = repository.create_ticket(
            title=data["title"],
            description=data["description"],
            user_type=data["user_type"],
            platform=data["platform"],
            category=data.get("category"),
            priority=data.get("priority"),
            login_credentials=data.get("login_credentials"),
            creator=request.user,
        )

        files = request.FILES.getlist("attachments") or request.FILES.getlist("attachment")
        if files:
            attachments = _save_attachments(files, ticket["ticket_id"])
            for attachment in attachments:
                ticket = repository.add_attachment(ticket["_id"], attachment)

        _notify("TICKET_CREATED", ticket)
        return Response(TicketDetailSerializer(repository.to_public(ticket)).data, status=201)


class PublicTicketCreateView(APIView):
    """No-login ticket submission — the URL meant to be shared directly with
    whoever is facing the issue, so they don't need an account. Creates a
    ticket with created_by=None and a created_by_snapshot built from the
    submitted name/email/phone instead of a logged-in user's profile.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PublicTicketCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        ticket = repository.create_ticket(
            title=data["title"],
            description=data["description"],
            user_type=data["user_type"],
            platform=data["platform"],
            category=data.get("category"),
            priority=data.get("priority"),
            login_credentials=data.get("login_credentials"),
            guest_name=data["name"],
            guest_email=data["email"],
            guest_phone=data["phone"],
        )

        files = request.FILES.getlist("attachments") or request.FILES.getlist("attachment")
        if files:
            attachments = _save_attachments(files, ticket["ticket_id"])
            for attachment in attachments:
                ticket = repository.add_attachment(ticket["_id"], attachment)

        _notify("TICKET_CREATED", ticket)
        return Response(TicketDetailSerializer(repository.to_public(ticket)).data, status=201)


class TicketDetailView(APIView):
    def get(self, request, ticket_id):
        ticket = repository.get_ticket(ticket_id)
        if not ticket:
            return Response({"detail": "Ticket not found."}, status=404)
        self.check_object_permissions(request, repository.to_public(ticket))
        return Response(TicketDetailSerializer(repository.to_public(ticket)).data)

    def get_permissions(self):
        return [IsTicketOwnerOrSupportStaff()]


class TicketAssignView(APIView):
    permission_classes = [IsSupportStaff]

    def patch(self, request, ticket_id):
        ticket = repository.get_ticket(ticket_id)
        if not ticket:
            return Response({"detail": "Ticket not found."}, status=404)

        serializer = AssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from apps.accounts.repository import find_user_by_id
        from apps.accounts.repository import to_public as user_to_public

        engineer_doc = find_user_by_id(serializer.validated_data["engineer_id"])
        engineer = SimpleNamespace(**user_to_public(engineer_doc))

        updated = repository.assign_ticket(ticket["_id"], engineer=engineer, actor=request.user)
        _notify("TICKET_ASSIGNED", updated)
        return Response(TicketDetailSerializer(repository.to_public(updated)).data)


class TicketStatusView(APIView):
    permission_classes = [IsSupportStaff]

    def patch(self, request, ticket_id):
        ticket = repository.get_ticket(ticket_id)
        if not ticket:
            return Response({"detail": "Ticket not found."}, status=404)

        serializer = StatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_status = serializer.validated_data["status"]
        note = serializer.validated_data.get("note")

        updated, error = repository.update_status(
            ticket["_id"], new_status=new_status, actor=request.user, note=note
        )
        if error:
            return Response({"detail": error}, status=400)

        template_key = constants.STATUS_TEMPLATE_MAP.get(new_status)
        if template_key:
            _notify(template_key, updated)
        if new_status == constants.RESOLVED:
            _notify("CSAT_CHECK", updated)

        return Response(TicketDetailSerializer(repository.to_public(updated)).data)


class TicketNoteView(APIView):
    permission_classes = [IsSupportStaff]

    def post(self, request, ticket_id):
        ticket = repository.get_ticket(ticket_id)
        if not ticket:
            return Response({"detail": "Ticket not found."}, status=404)

        serializer = NoteCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        updated = repository.add_note(
            ticket["_id"], actor=request.user, note=serializer.validated_data["note"]
        )
        return Response(TicketDetailSerializer(repository.to_public(updated)).data, status=201)


class TicketHistoryView(APIView):
    def get(self, request, ticket_id):
        ticket = repository.get_ticket(ticket_id)
        if not ticket:
            return Response({"detail": "Ticket not found."}, status=404)
        self.check_object_permissions(request, repository.to_public(ticket))
        from core.utils import serialize_doc

        return Response(serialize_doc({"activity_log": ticket.get("activity_log", [])}))

    def get_permissions(self):
        return [IsTicketOwnerOrSupportStaff()]


class TicketCSATResponseView(APIView):
    """Manual/internal recording of a user's satisfaction reply. The Karix
    inbound webhook (apps.notifications) calls the same repository function
    for replies that arrive over WhatsApp."""

    permission_classes = [IsSupportStaff]

    def post(self, request, ticket_id):
        ticket = repository.get_ticket(ticket_id)
        if not ticket:
            return Response({"detail": "Ticket not found."}, status=404)

        serializer = CSATResponseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        updated, error = repository.record_csat_response(
            ticket["_id"], satisfied=serializer.validated_data["satisfied"], actor=request.user
        )
        if error:
            return Response({"detail": error}, status=400)

        template_key = "TICKET_CLOSED" if updated["status"] == constants.CLOSED else "TICKET_REOPENED"
        _notify(template_key, updated)
        return Response(TicketDetailSerializer(repository.to_public(updated)).data)
