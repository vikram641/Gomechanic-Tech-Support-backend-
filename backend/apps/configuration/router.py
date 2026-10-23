from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from apps.configuration import repository
from apps.configuration.schemas import (
    OptionCreate,
    OptionResponse,
    OptionUpdate,
    PriorityCreate,
    PriorityResponse,
    PriorityUpdate,
    SLARuleCreate,
    SLARuleResponse,
    SLARuleUpdate,
    WhatsAppTemplateCreate,
    WhatsAppTemplateResponse,
    WhatsAppTemplateUpdate,
)
from core.deps import MongoUser, require_admin
from core.errors import AppError


def build_dropdown_router(*, path_segment, collection_name, response_schema, create_schema, update_schema):
    """One generic implementation shared by all six dropdown/config types
    (user types, platforms, ticket categories, ticket priorities, WhatsApp
    template keys, SLA rules) — reads are public, writes are admin-only."""

    router = APIRouter(prefix=f"/api/config/{path_segment}", tags=["configuration"])

    @router.get("/", response_model=list[response_schema])
    def list_options(active_only: str = "true"):
        is_active_only = active_only.lower() != "false"
        options = repository.list_options(collection_name, active_only=is_active_only)
        return [response_schema(**repository.to_public(o)) for o in options]

    @router.post("/", response_model=response_schema, status_code=201)
    def create_option(payload: create_schema, _admin: Annotated[MongoUser, Depends(require_admin)]):
        try:
            doc = repository.create_option(collection_name, payload.model_dump())
        except ValueError as exc:
            raise AppError(message=str(exc)) from exc
        return response_schema(**repository.to_public(doc))

    @router.get("/{option_id}/", response_model=response_schema)
    def get_option(option_id: str):
        option = repository.get_option(collection_name, option_id)
        if not option:
            raise HTTPException(status_code=404, detail="Not found.")
        return response_schema(**repository.to_public(option))

    @router.patch("/{option_id}/", response_model=response_schema)
    def update_option(
        option_id: str, payload: update_schema, _admin: Annotated[MongoUser, Depends(require_admin)]
    ):
        if not repository.get_option(collection_name, option_id):
            raise HTTPException(status_code=404, detail="Not found.")
        updated = repository.update_option(collection_name, option_id, payload.model_dump(exclude_unset=True))
        return response_schema(**repository.to_public(updated))

    @router.delete("/{option_id}/", status_code=204, response_model=None)
    def delete_option(option_id: str, _admin: Annotated[MongoUser, Depends(require_admin)]):
        if not repository.get_option(collection_name, option_id):
            raise HTTPException(status_code=404, detail="Not found.")
        repository.delete_option(collection_name, option_id)
        return None

    return router


user_types_router = build_dropdown_router(
    path_segment="user-types",
    collection_name=repository.USER_TYPES,
    response_schema=OptionResponse,
    create_schema=OptionCreate,
    update_schema=OptionUpdate,
)

platforms_router = build_dropdown_router(
    path_segment="platforms",
    collection_name=repository.PLATFORMS,
    response_schema=OptionResponse,
    create_schema=OptionCreate,
    update_schema=OptionUpdate,
)

ticket_categories_router = build_dropdown_router(
    path_segment="ticket-categories",
    collection_name=repository.TICKET_CATEGORIES,
    response_schema=OptionResponse,
    create_schema=OptionCreate,
    update_schema=OptionUpdate,
)

ticket_priorities_router = build_dropdown_router(
    path_segment="ticket-priorities",
    collection_name=repository.TICKET_PRIORITIES,
    response_schema=PriorityResponse,
    create_schema=PriorityCreate,
    update_schema=PriorityUpdate,
)

whatsapp_templates_router = build_dropdown_router(
    path_segment="whatsapp-templates",
    collection_name=repository.WHATSAPP_TEMPLATES,
    response_schema=WhatsAppTemplateResponse,
    create_schema=WhatsAppTemplateCreate,
    update_schema=WhatsAppTemplateUpdate,
)

sla_rules_router = build_dropdown_router(
    path_segment="sla-rules",
    collection_name=repository.SLA_RULES,
    response_schema=SLARuleResponse,
    create_schema=SLARuleCreate,
    update_schema=SLARuleUpdate,
)

all_routers = (
    user_types_router,
    platforms_router,
    ticket_categories_router,
    ticket_priorities_router,
    whatsapp_templates_router,
    sla_rules_router,
)
