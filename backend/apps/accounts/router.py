from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from apps.accounts import repository
from apps.accounts.schemas import (
    AdminUserCreateRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    UserResponse,
    UserUpdateRequest,
)
from core.deps import MongoUser, get_current_user, require_admin, require_support_staff
from core.errors import AppError
from core.jwt_utils import TokenError, create_access_token, create_token_pair, decode_token
from core.pagination import PageParams, build_page, page_params
from core.utils import to_object_id

auth_router = APIRouter(prefix="/api/auth", tags=["auth"])
users_router = APIRouter(prefix="/api/users", tags=["users"])


@auth_router.post("/register", response_model=None, status_code=201)
def register(payload: RegisterRequest):
    from apps.configuration.repository import is_active_option

    if not is_active_option("user_types", payload.user_type):
        raise AppError(
            field="user_type",
            message="Unknown or inactive user type. Check /api/config/user-types/ for valid values.",
        )

    try:
        user = repository.create_user(
            name=payload.name,
            email=payload.email,
            password=payload.password,
            phone=payload.phone,
            role="user",
            user_type=payload.user_type,
        )
    except ValueError as exc:
        raise AppError(message=str(exc)) from exc

    tokens = create_token_pair(user)
    return {"user": UserResponse(**repository.to_public(user)), **tokens}


@auth_router.post("/login", response_model=None)
def login(payload: LoginRequest):
    user = repository.verify_credentials(payload.email, payload.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    if not user.get("is_active", True):
        raise HTTPException(status_code=403, detail="This account has been deactivated.")

    tokens = create_token_pair(user)
    return {"user": UserResponse(**repository.to_public(user)), **tokens}


@auth_router.post("/refresh", response_model=None)
def refresh(payload: RefreshRequest):
    try:
        token_payload = decode_token(payload.refresh, expected_type="refresh")
    except TokenError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    user = repository.find_user_by_id(token_payload["sub"])
    if not user or not user.get("is_active", True):
        raise HTTPException(status_code=401, detail="User not found or inactive.")

    return {"access": create_access_token(user)}


@auth_router.get("/me", response_model=UserResponse)
def get_me(current_user: Annotated[MongoUser, Depends(get_current_user)]):
    return UserResponse(**repository.to_public(current_user._doc))


@auth_router.patch("/me", response_model=UserResponse)
def update_me(payload: UserUpdateRequest, current_user: Annotated[MongoUser, Depends(get_current_user)]):
    updates = payload.model_dump(exclude_unset=True)
    updated = repository.update_user(current_user.id, updates)
    return UserResponse(**repository.to_public(updated))


@users_router.get("/", response_model=None)
def list_users(
    *,
    pagination: Annotated[PageParams, Depends(page_params)],
    _staff: Annotated[MongoUser, Depends(require_support_staff)],
    role: str | None = None,
    search: str | None = None,
):
    users, total = repository.list_users(
        role=role, search=search, skip=pagination.skip, limit=pagination.page_size
    )
    data = [UserResponse(**repository.to_public(u)) for u in users]
    return build_page(data, total, pagination.page, pagination.page_size)


@users_router.post("/", response_model=UserResponse, status_code=201)
def create_user(payload: AdminUserCreateRequest, _admin: Annotated[MongoUser, Depends(require_admin)]):
    try:
        user = repository.create_user(
            name=payload.name,
            email=payload.email,
            password=payload.password,
            phone=payload.phone,
            role=payload.role,
            user_type=payload.user_type,
        )
    except ValueError as exc:
        raise AppError(message=str(exc)) from exc
    return UserResponse(**repository.to_public(user))


def _get_or_404(user_id: str):
    oid = to_object_id(user_id)
    user = repository.find_user_by_id(oid) if oid else None
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return user


@users_router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: str, _admin: Annotated[MongoUser, Depends(require_admin)]):
    user = _get_or_404(user_id)
    return UserResponse(**repository.to_public(user))


@users_router.patch("/{user_id}", response_model=UserResponse)
def update_user(user_id: str, payload: UserUpdateRequest, _admin: Annotated[MongoUser, Depends(require_admin)]):
    _get_or_404(user_id)
    updates = payload.model_dump(exclude_unset=True)
    updated = repository.update_user(user_id, updates)
    return UserResponse(**repository.to_public(updated))


@users_router.delete("/{user_id}", status_code=204, response_model=None)
def delete_user(user_id: str, _admin: Annotated[MongoUser, Depends(require_admin)]):
    _get_or_404(user_id)
    repository.deactivate_user(user_id)
    return None
