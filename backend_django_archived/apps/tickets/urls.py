from django.urls import path

from apps.tickets import views

urlpatterns = [
    path("", views.TicketListCreateView.as_view(), name="ticket-list-create"),
    # Must precede "<str:ticket_id>" — otherwise that catch-all would swallow
    # "public" as a ticket_id lookup instead of reaching this view.
    path("public", views.PublicTicketCreateView.as_view(), name="ticket-public-create"),
    path("<str:ticket_id>", views.TicketDetailView.as_view(), name="ticket-detail"),
    path("<str:ticket_id>/assign", views.TicketAssignView.as_view(), name="ticket-assign"),
    path("<str:ticket_id>/status", views.TicketStatusView.as_view(), name="ticket-status"),
    path("<str:ticket_id>/notes", views.TicketNoteView.as_view(), name="ticket-notes"),
    path("<str:ticket_id>/history", views.TicketHistoryView.as_view(), name="ticket-history"),
    path(
        "<str:ticket_id>/csat-response",
        views.TicketCSATResponseView.as_view(),
        name="ticket-csat-response",
    ),
]
