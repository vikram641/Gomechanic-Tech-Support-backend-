from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path

urlpatterns = [
    path("api/auth/", include("apps.accounts.urls")),
    path("api/users/", include("apps.accounts.user_urls")),
    path("api/config/", include("apps.configuration.urls")),
    path("api/tickets/", include("apps.tickets.urls")),
    path("api/notifications/", include("apps.notifications.urls")),
    path("api/analytics/", include("apps.analytics.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
