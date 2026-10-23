from django.urls import path

from apps.accounts import views

# Admin-only user management — mounted at /api/users/ (separate from
# /api/auth/ which handles register/login/refresh/me for any caller).
urlpatterns = [
    path("", views.UserListCreateView.as_view(), name="user-list-create"),
    path("<str:user_id>", views.UserDetailView.as_view(), name="user-detail"),
]
