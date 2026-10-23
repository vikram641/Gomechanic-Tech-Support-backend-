from django.urls import path

from apps.notifications import views

urlpatterns = [
    path("logs/", views.NotificationLogListView.as_view(), name="notification-logs"),
    path("webhook/karix", views.KarixWebhookView.as_view(), name="karix-webhook"),
]
