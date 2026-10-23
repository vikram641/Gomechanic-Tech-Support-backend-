from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.notifications import repository
from apps.notifications.serializers import KarixWebhookSerializer, NotificationLogSerializer
from core.pagination import DefaultPagination
from core.permissions import IsSupportStaff


class NotificationLogListView(APIView):
    permission_classes = [IsSupportStaff]

    def get(self, request):
        logs, total, page, page_size = repository.list_logs(
            ticket_id=request.query_params.get("ticket_id"),
            status=request.query_params.get("status"),
            request=request,
        )
        paginator = DefaultPagination()
        items = paginator.paginate_list(request, logs, total)
        data = NotificationLogSerializer([repository.to_public(l) for l in items], many=True).data
        return paginator.get_paginated_response(data)


def _interpret_satisfaction_reply(text):
    """Best-effort free-text parse of a user's WhatsApp reply. Karix likely
    supports interactive reply buttons with fixed payloads instead of free
    text — switch to matching those exact payload IDs once confirmed, which
    would remove this guesswork entirely."""
    normalized = (text or "").strip().lower()
    exact_no = {"no", "not satisfied", "not resolved"}
    exact_yes = {"yes", "satisfied", "resolved"}
    if normalized in exact_no:
        return False
    if normalized in exact_yes:
        return True
    if "not satisfied" in normalized or "not resolved" in normalized:
        return False
    if "satisfied" in normalized or "resolved" in normalized:
        return True
    return None


class KarixWebhookView(APIView):
    """Receives inbound WhatsApp replies from Karix — specifically the
    user's 'Satisfied' / 'Not Satisfied' answer to the post-resolution CSAT
    check (see Ticket Workflow step 8-9 in the FRD). No auth here since
    webhooks call in anonymously; add a shared-secret header or IP allowlist
    once Karix's webhook signing scheme is confirmed.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = KarixWebhookSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        phone = data["source"]

        satisfied = _interpret_satisfaction_reply(data.get("text"))
        if satisfied is None:
            return Response(
                {"detail": "Couldn't interpret reply as satisfied / not satisfied."}, status=400
            )

        from apps.tickets.repository import collection as tickets_collection
        from apps.tickets.repository import record_csat_response

        ticket = tickets_collection().find_one(
            {"created_by_snapshot.phone": phone, "csat_status": "pending"},
            sort=[("resolved_at", -1)],
        )
        if not ticket:
            return Response(
                {"detail": "No ticket awaiting a satisfaction response for this number."},
                status=404,
            )

        updated, error = record_csat_response(ticket["_id"], satisfied=satisfied)
        if error:
            return Response({"detail": error}, status=400)

        from apps.notifications.karix_client import KarixWhatsAppService

        template_key = "TICKET_CLOSED" if satisfied else "TICKET_REOPENED"
        try:
            KarixWhatsAppService().send_template_message(
                to_phone=phone, template_key=template_key, ticket=updated
            )
        except Exception:
            pass

        return Response({"ticket_id": updated["ticket_id"], "status": updated["status"]})
