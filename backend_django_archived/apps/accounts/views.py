from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts import repository
from apps.accounts.serializers import (
    AdminUserCreateSerializer,
    LoginSerializer,
    RefreshSerializer,
    RegisterSerializer,
    UserSerializer,
    UserUpdateSerializer,
)
from core.jwt_utils import TokenError, create_access_token, create_token_pair, decode_token
from core.pagination import DefaultPagination
from core.permissions import IsAdmin, IsSupportStaff
from core.utils import to_object_id


class RegisterView(APIView):
    """Public sign-up for ticket-raising users (CR, Garage Owner, etc.)."""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            user = repository.create_user(
                name=data["name"],
                email=data["email"],
                password=data["password"],
                phone=data.get("phone"),
                role="user",
                user_type=data["user_type"],
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)

        tokens = create_token_pair(user)
        return Response(
            {"user": UserSerializer(repository.to_public(user)).data, **tokens}, status=201
        )


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user = repository.verify_credentials(data["email"], data["password"])
        if not user:
            return Response({"detail": "Invalid email or password."}, status=401)
        if not user.get("is_active", True):
            return Response({"detail": "This account has been deactivated."}, status=403)

        tokens = create_token_pair(user)
        return Response({"user": UserSerializer(repository.to_public(user)).data, **tokens})


class RefreshView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RefreshSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            payload = decode_token(serializer.validated_data["refresh"], expected_type="refresh")
        except TokenError as exc:
            return Response({"detail": str(exc)}, status=401)

        user = repository.find_user_by_id(payload["sub"])
        if not user or not user.get("is_active", True):
            return Response({"detail": "User not found or inactive."}, status=401)

        return Response({"access": create_access_token(user)})


class MeView(APIView):
    def get(self, request):
        return Response(UserSerializer(repository.to_public(request.user._doc)).data)

    def patch(self, request):
        serializer = UserUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated = repository.update_user(request.user.id, serializer.validated_data)
        return Response(UserSerializer(repository.to_public(updated)).data)


class UserListCreateView(APIView):
    """List: any support staff (admin or support_engineer) — needed so an
    engineer can see who's available to assign/reassign a ticket to, not
    just admins. Create: admin-only, since this creates real accounts
    (support engineers, admins, or manually-added ticket-raising users)."""

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAdmin()]
        return [IsSupportStaff()]

    def get(self, request):
        role = request.query_params.get("role")
        search = request.query_params.get("search")
        users, total, page, page_size = repository.list_users(
            role=role, search=search, request=request
        )
        paginator = DefaultPagination()
        items = paginator.paginate_list(request, users, total)
        data = UserSerializer([repository.to_public(u) for u in items], many=True).data
        return paginator.get_paginated_response(data)

    def post(self, request):
        serializer = AdminUserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            user = repository.create_user(
                name=data["name"],
                email=data["email"],
                password=data["password"],
                phone=data.get("phone"),
                role=data["role"],
                user_type=data.get("user_type"),
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(UserSerializer(repository.to_public(user)).data, status=201)


class UserDetailView(APIView):
    permission_classes = [IsAdmin]

    def _get_or_404(self, user_id):
        oid = to_object_id(user_id)
        user = repository.find_user_by_id(oid) if oid else None
        return user

    def get(self, request, user_id):
        user = self._get_or_404(user_id)
        if not user:
            return Response({"detail": "User not found."}, status=404)
        return Response(UserSerializer(repository.to_public(user)).data)

    def patch(self, request, user_id):
        user = self._get_or_404(user_id)
        if not user:
            return Response({"detail": "User not found."}, status=404)
        serializer = UserUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated = repository.update_user(user_id, serializer.validated_data)
        return Response(UserSerializer(repository.to_public(updated)).data)

    def delete(self, request, user_id):
        user = self._get_or_404(user_id)
        if not user:
            return Response({"detail": "User not found."}, status=404)
        repository.deactivate_user(user_id)
        return Response(status=204)
