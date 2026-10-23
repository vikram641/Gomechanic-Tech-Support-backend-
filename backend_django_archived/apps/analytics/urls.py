from django.urls import path

from apps.analytics import views

urlpatterns = [
    path("summary", views.AnalyticsSummaryView.as_view(), name="analytics-summary"),
    path("export/excel", views.AnalyticsExportExcelView.as_view(), name="analytics-export-excel"),
    path("export/pdf", views.AnalyticsExportPDFView.as_view(), name="analytics-export-pdf"),
]
