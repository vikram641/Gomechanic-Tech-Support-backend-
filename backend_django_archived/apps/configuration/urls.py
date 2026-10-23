from django.urls import path

from apps.configuration import views

urlpatterns = [
    path("user-types/", views.UserTypeListCreateView.as_view(), name="user-types"),
    path("user-types/<str:option_id>/", views.UserTypeDetailView.as_view(), name="user-type-detail"),
    path("platforms/", views.PlatformListCreateView.as_view(), name="platforms"),
    path("platforms/<str:option_id>/", views.PlatformDetailView.as_view(), name="platform-detail"),
    path(
        "ticket-categories/",
        views.TicketCategoryListCreateView.as_view(),
        name="ticket-categories",
    ),
    path(
        "ticket-categories/<str:option_id>/",
        views.TicketCategoryDetailView.as_view(),
        name="ticket-category-detail",
    ),
    path(
        "ticket-priorities/",
        views.TicketPriorityListCreateView.as_view(),
        name="ticket-priorities",
    ),
    path(
        "ticket-priorities/<str:option_id>/",
        views.TicketPriorityDetailView.as_view(),
        name="ticket-priority-detail",
    ),
    path(
        "whatsapp-templates/",
        views.WhatsAppTemplateListCreateView.as_view(),
        name="whatsapp-templates",
    ),
    path(
        "whatsapp-templates/<str:option_id>/",
        views.WhatsAppTemplateDetailView.as_view(),
        name="whatsapp-template-detail",
    ),
    path("sla-rules/", views.SLARuleListCreateView.as_view(), name="sla-rules"),
    path("sla-rules/<str:option_id>/", views.SLARuleDetailView.as_view(), name="sla-rule-detail"),
]
