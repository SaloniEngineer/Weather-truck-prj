from django.urls import path
from routing.views import health_check, GeocodeView, AnalyzeRoutesView

urlpatterns = [
    path("health/", health_check, name="health_check"),
    path("geocode/", GeocodeView.as_view(), name="geocode"),
    path("routes/analyze/", AnalyzeRoutesView.as_view(), name="analyze_routes"),
]
