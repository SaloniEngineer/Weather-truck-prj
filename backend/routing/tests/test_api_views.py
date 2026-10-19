"""
Integration Tests for Routing API Views.
"""

import pytest
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestApiEndpoints:
    def setup_method(self):
        self.client = APIClient()

    def test_health_check(self):
        response = self.client.get("/api/health/")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_geocode_success(self):
        response = self.client.get("/api/geocode/?q=Chicago")
        assert response.status_code == 200
        data = response.json()
        assert "lat" in data
        assert "lon" in data
        assert pytest.approx(data["lat"], abs=0.5) == 41.87

    def test_geocode_missing_query(self):
        response = self.client.get("/api/geocode/")
        assert response.status_code == 400

    def test_analyze_routes_missing_params(self):
        response = self.client.post("/api/routes/analyze/", {}, format="json")
        assert response.status_code == 400
