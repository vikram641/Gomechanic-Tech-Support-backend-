import uuid
from datetime import datetime
from types import SimpleNamespace
from typing import Annotated, Optional

from dateutil import parser as date_parser
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import EmailStr

from apps.tickets import constants, repository
from apps.tickets.schemas import (
    AssignRequest,
    CSATResponseRequest,
    NoteCreateRequest,
    StatusUpdateRequest,
    TicketDetailResponse,
    TicketListItemResponse,
)
from core.config import settings
from core.deps import MongoUser, STAFF_ROLES, get_current_user, require_support_staff
from core.errors import AppError
from core.pagination import PageParams, build_page, page_params
from core.utils import now

router = APIRouter(prefix="/api/tickets", tags=["tickets"])


def _parse_date(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return date_parser.parse(value)
    except (ValueError, OverflowError):
        return None


async def _save_attachments(files: list[UploadFile], ticket_id: str) -> list[dict]:
    saved = []
    upload_dir = settings.media_root_path / "uploads" / "tickets" / ticket_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    for f in files:
        if not f.filename:
            continue
        ext = f.filename.rsplit(".", 1)[-1] if "." in f.filename else ""
        name = uuid.uuid4().hex + (f".{ext}" if ext else "")
        dest = upload_dir / name
        contents = await f.read()
        dest.write_bytes(contents)
        url = f"{settings.MEDIA_URL}uploads/tickets/{ticket_id}/{name}"
        saved.append(
            {
                "filename": f.filename,
                "url": url,
                "content_type": f.content_type or "",
                "uploaded_at": now(),
            }
        )
    return saved


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


def _validate_active_option(field: str, collection_name: str, value: Optional[str], message: str):
    from apps.configuration.repository import is_active_option

    if value and not is_active_option(collection_name, value):
        raise AppError(field=field, message=message)


def _validate_required_active_option(field: str, collection_name: str, value: str, message: str):
    from apps.configuration.repository import is_active_option

    if not is_active_option(collection_name, value):
        raise AppError(field=field, message=message)


def _validate_ticket_fields(*, user_type: str, platform: str, category: Optional[str], priority: Optional[str]):
    from apps.configuration.repository import PLATFORMS, TICKET_CATEGORIES, TICKET_PRIORITIES, USER_TYPES

    _validate_required_active_option("user_type", USER_TYPES, user_type, "Unknown or inactive user type.")
    _validate_required_active_option("platform", PLATFORMS, platform, "Unknown or inactive platform.")
    _validate_active_option("category", TICKET_CATEGORIES, category, "Unknown or inactive ticket category.")
    _validate_active_option("priority", TICKET_PRIORITIES, priority, "Unknown or inactive priority.")


@router.get("/", response_model=None)
def list_tickets(
    *,
    pagination: Annotated[PageParams, Depends(page_params)],
    current_user: Annotated[MongoUser, Depends(get_current_user)],
    status: str | None = None,
    user_type: str | None = None,
    platform: str | None = None,
    priority: str | None = None,
    assigned_to: str | None = None,
    created_by: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    search: str | None = None,
):
    is_end_user = current_user.role == "user"
    effective_created_by = current_user.id if is_end_user else created_by

    items, total = repository.list_tickets(
        status=status,
        user_type=user_type,
        platform=platform,
        priority=priority,
        assigned_to=assigned_to,
        created_by=effective_created_by,
        date_from=_parse_date(date_from),
        date_to=_parse_date(date_to),
        search=search,
        skip=pagination.skip,
        limit=pagination.page_size,
    )
    data = [TicketListItemResponse(**repository.to_public(t)) for t in items]
    return build_page(data, total, pagination.page, pagination.page_size)


@router.post("/", response_model=TicketDetailResponse, status_code=201)
async def create_ticket(
    *,
    current_user: Annotated[MongoUser, Depends(get_current_user)],
    title: Annotated[str, Form(max_length=200)],
    description: Annotated[str, Form()],
    user_type: Annotated[str, Form(max_length=150)],
    platform: Annotated[str, Form(max_length=150)],
    category: Annotated[Optional[str], Form(max_length=150)] = None,
    priority: Annotated[Optional[str], Form(max_length=150)] = None,
    login_credentials: Annotated[Optional[str], Form()] = None,
    attachments: Annotated[list[UploadFile], File()] = [],
    attachment: Annotated[list[UploadFile], File()] = [],
):
    _validate_ticket_fields(user_type=user_type, platform=platform, category=category, priority=priority)

    ticket = repository.create_ticket(
        title=title,
        description=description,
        user_type=user_type,
        platform=platform,
        category=category,
        priority=priority,
        login_credentials=login_credentials,
        creator=current_user,
    )

    files = [f for f in (attachments or attachment) if f.filename]
    if files:
        saved = await _save_attachments(files, ticket["ticket_id"])
        for saved_attachment in saved:
            ticket = repository.add_attachment(ticket["_id"], saved_attachment)

    _notify("TICKET_CREATED", ticket)
    return TicketDetailResponse(**repository.to_public(ticket))


@router.post("/public", response_model=TicketDetailResponse, status_code=201)
async def create_public_ticket(
    *,
    title: Annotated[str, Form(max_length=200)],
    description: Annotated[str, Form()],
    user_type: Annotated[str, Form(max_length=150)],
    platform: Annotated[str, Form(max_length=150)],
    name: Annotated[str, Form(max_length=150)],
    email: Annotated[EmailStr, Form()],
    phone: Annotated[str, Form(max_length=20)],
    category: Annotated[Optional[str], Form(max_length=150)] = None,
    priority: Annotated[Optional[str], Form(max_length=150)] = None,
    login_credentials: Annotated[Optional[str], Form()] = None,
    attachments: Annotated[list[UploadFile], File()] = [],
    attachment: Annotated[list[UploadFile], File()] = [],
):
    _validate_ticket_fields(user_type=user_type, platform=platform, category=category, priority=priority)

    ticket = repository.create_ticket(
        title=title,
        description=description,
        user_type=user_type,
        platform=platform,
        category=category,
        priority=priority,
        login_credentials=login_credentials,
        guest_name=name,
        guest_email=email,
        guest_phone=phone,
    )

    files = [f for f in (attachments or attachment) if f.filename]
    if files:
        saved = await _save_attachments(files, ticket["ticket_id"])
        for saved_attachment in saved:
            ticket = repository.add_attachment(ticket["_id"], saved_attachment)

    _notify("TICKET_CREATED", ticket)
    return TicketDetailResponse(**repository.to_public(ticket))


def _get_ticket_or_404(ticket_id: str) -> dict:
    ticket = repository.get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found.")
    return ticket


def _check_owner_or_staff(ticket: dict, current_user: MongoUser):
    if current_user.role in STAFF_ROLES:
        return
    if str(ticket.get("created_by")) != str(current_user.id):
        raise HTTPException(status_code=403, detail="You do not have permission to perform this action.")


@router.get("/{ticket_id}", response_model=TicketDetailResponse)
def get_ticket(ticket_id: str, current_user: Annotated[MongoUser, Depends(get_current_user)]):
    ticket = _get_ticket_or_404(ticket_id)
    _check_owner_or_staff(ticket, current_user)
    return TicketDetailResponse(**repository.to_public(ticket))


@router.patch("/{ticket_id}/assign", response_model=TicketDetailResponse)
def assign_ticket(
    ticket_id: str, payload: AssignRequest, current_user: Annotated[MongoUser, Depends(require_support_staff)]
):
    from apps.accounts.repository import find_user_by_id
    from apps.accounts.repository import to_public as user_to_public

    ticket = _get_ticket_or_404(ticket_id)

    engineer_doc = find_user_by_id(payload.engineer_id)
    if not engineer_doc:
        raise AppError(field="engineer_id", message="Engineer not found.")
    if engineer_doc.get("role") not in STAFF_ROLES:
        raise AppError(field="engineer_id", message="This user is not a support engineer or admin.")
    if not engineer_doc.get("is_active", True):
        raise AppError(field="engineer_id", message="This engineer's account is deactivated.")

    engineer = SimpleNamespace(**user_to_public(engineer_doc))
    updated = repository.assign_ticket(ticket["_id"], engineer=engineer, actor=current_user)
    _notify("TICKET_ASSIGNED", updated)
    return TicketDetailResponse(**repository.to_public(updated))


@router.patch("/{ticket_id}/status", response_model=TicketDetailResponse)
def update_ticket_status(
    ticket_id: str,
    payload: StatusUpdateRequest,
    current_user: Annotated[MongoUser, Depends(require_support_staff)],
):
    if payload.status not in constants.ALL_STATUSES:
        raise AppError(field="status", message=f'"{payload.status}" is not a valid choice.')

    ticket = _get_ticket_or_404(ticket_id)
    updated, error = repository.update_status(
        ticket["_id"], new_status=payload.status, actor=current_user, note=payload.note
    )
    if error:
        raise AppError(message=error)

    template_key = constants.STATUS_TEMPLATE_MAP.get(payload.status)
    if template_key:
        _notify(template_key, updated)
    if payload.status == constants.RESOLVED:
        _notify("CSAT_CHECK", updated)

    return TicketDetailResponse(**repository.to_public(updated))


@router.post("/{ticket_id}/notes", response_model=TicketDetailResponse, status_code=201)
def add_ticket_note(
    ticket_id: str, payload: NoteCreateRequest, current_user: Annotated[MongoUser, Depends(require_support_staff)]
):
    _get_ticket_or_404(ticket_id)
    updated = repository.add_note(ticket_id, actor=current_user, note=payload.note)
    return TicketDetailResponse(**repository.to_public(updated))


@router.get("/{ticket_id}/history", response_model=None)
def get_ticket_history(ticket_id: str, current_user: Annotated[MongoUser, Depends(get_current_user)]):
    from core.utils import serialize_doc

    ticket = _get_ticket_or_404(ticket_id)
    _check_owner_or_staff(ticket, current_user)
    return serialize_doc({"activity_log": ticket.get("activity_log", [])})


@router.post("/{ticket_id}/csat-response", response_model=TicketDetailResponse)
def record_csat_response(
    ticket_id: str,
    payload: CSATResponseRequest,
    current_user: Annotated[MongoUser, Depends(require_support_staff)],
):
    ticket = _get_ticket_or_404(ticket_id)
    updated, error = repository.record_csat_response(
        ticket["_id"], satisfied=payload.satisfied, actor=current_user
    )
    if error:
        raise AppError(message=error)

    template_key = "TICKET_CLOSED" if updated["status"] == constants.CLOSED else "TICKET_REOPENED"
    _notify(template_key, updated)
    return TicketDetailResponse(**repository.to_public(updated))
