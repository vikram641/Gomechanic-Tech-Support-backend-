from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from apps.notifications import repository
from apps.notifications.schemas import KarixWebhookRequest, NotificationLogResponse
from core.deps import MongoUser, require_support_staff
from core.errors import AppError
from core.pagination import PageParams, build_page, page_params

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("/logs/", response_model=None)
def list_notification_logs(
    *,
    pagination: Annotated[PageParams, Depends(page_params)],
    _staff: Annotated[MongoUser, Depends(require_support_staff)],
    ticket_id: str | None = None,
    status: str | None = None,
):
    logs, total = repository.list_logs(
        ticket_id=ticket_id, status=status, skip=pagination.skip, limit=pagination.page_size
    )
    data = [NotificationLogResponse(**repository.to_public(log)) for log in logs]
    return build_page(data, total, pagination.page, pagination.page_size)


def _interpret_satisfaction_reply(text: str | None) -> bool | None:
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


@router.post("/webhook/karix", response_model=None)
def karix_webhook(payload: KarixWebhookRequest):
    """Receives inbound WhatsApp replies from Karix — specifically the
    user's 'Satisfied' / 'Not Satisfied' answer to the post-resolution CSAT
    check (see Ticket Workflow step 8-9 in the FRD). No auth here since
    webhooks call in anonymously; add a shared-secret header or IP allowlist
    once Karix's webhook signing scheme is confirmed.
    """
    phone = payload.source

    satisfied = _interpret_satisfaction_reply(payload.text)
    if satisfied is None:
        raise AppError(message="Couldn't interpret reply as satisfied / not satisfied.")

    from apps.tickets.repository import collection as tickets_collection
    from apps.tickets.repository import record_csat_response

    ticket = tickets_collection().find_one(
        {"created_by_snapshot.phone": phone, "csat_status": "pending"},
        sort=[("resolved_at", -1)],
    )
    if not ticket:
        raise HTTPException(
            status_code=404, detail="No ticket awaiting a satisfaction response for this number."
        )

    updated, error = record_csat_response(ticket["_id"], satisfied=satisfied)
    if error:
        raise AppError(message=error)

    from apps.notifications.karix_client import KarixWhatsAppService

    template_key = "TICKET_CLOSED" if satisfied else "TICKET_REOPENED"
    try:
        KarixWhatsAppService().send_template_message(to_phone=phone, template_key=template_key, ticket=updated)
    except Exception:
        pass

    return {"ticket_id": updated["ticket_id"], "status": updated["status"]}
