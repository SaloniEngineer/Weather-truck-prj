"""
API Views and Controllers for Weather-Aware Truck Routing.
"""

import logging
from datetime import datetime, timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view

from routing.services.geocode_service import geocode_location
from routing.services.routing_service import get_3_routes
from routing.services.sampling_service import sample_route_polyline
from routing.services.weather_service import enrich_checkpoints_with_weather, parse_iso_datetime
from routing.services.risk_service import calculate_checkpoint_risk
from routing.services.recommend_service import rank_and_recommend_routes
from routing.services.corridor_heatmap_service import get_corridor_48h_heatmap

logger = logging.getLogger(__name__)


@api_view(["GET"])
def health_check(request):
    """Simple health check endpoint for Render/Railway/uptime monitors."""
    return Response({"status": "healthy", "service": "weather-truck-routing-api"})


class GeocodeView(APIView):
    """
    GET /api/geocode/?q=<location>
    Resolves location query to coordinates.
    """

    def get(self, request):
        query = request.query_params.get("q", "").strip()
        if not query:
            return Response(
                {"error": "Query parameter 'q' is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            result = geocode_location(query)
            return Response(result)
        except Exception as exc:
            logger.warning(f"Geocoding error for '{query}': {exc}")
            return Response({"error": str(exc)}, status=status.HTTP_404_NOT_FOUND)


class AnalyzeRoutesView(APIView):
    """
    POST /api/routes/analyze/
    Comprehensive weather-aware truck route analysis.

    Payload:
    {
        "origin": "Chicago, IL",
        "destination": "Denver, CO",
        "departure_time": "2026-10-18T22:30:00Z",
        "load_weight": 35000,
        "interval_miles": 25
    }
    """

    def post(self, request):
        data = request.data or {}

        origin_query = str(data.get("origin", "")).strip()
        destination_query = str(data.get("destination", "")).strip()

        if not origin_query or not destination_query:
            return Response(
                {"error": "Both 'origin' and 'destination' fields are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Parse departure time
        dep_time_raw = data.get("departure_time")
        if dep_time_raw:
            departure_time = parse_iso_datetime(str(dep_time_raw))
        else:
            departure_time = datetime.now(timezone.utc)

        # Parse truck cargo load
        try:
            load_weight = float(data.get("load_weight", 30000.0))
            if load_weight < 0:
                load_weight = 0.0
        except (ValueError, TypeError):
            load_weight = 30000.0

        # Parse sampling interval (10, 25, or 50 miles)
        try:
            interval_miles = float(data.get("interval_miles", 25.0))
            if interval_miles not in [10.0, 25.0, 50.0]:
                interval_miles = 25.0
        except (ValueError, TypeError):
            interval_miles = 25.0

        try:
            # 1. Geocode origin and destination
            origin_info = geocode_location(origin_query)
            destination_info = geocode_location(destination_query)

            # 2. Generate 3 route options
            routes = get_3_routes(
                origin_lat=origin_info["lat"],
                origin_lon=origin_info["lon"],
                dest_lat=destination_info["lat"],
                dest_lon=destination_info["lon"],
                origin_name=origin_info["name"],
                dest_name=destination_info["name"],
            )

            if not routes:
                return Response(
                    {"error": "Could not compute routing paths between the specified locations."},
                    status=status.HTTP_502_BAD_GATEWAY,
                )

            # 3. Sample polyline checkpoints for each route
            for route in routes:
                coords = route["geometry"]["coordinates"]  # [[lon, lat], ...]
                duration_sec = route["duration_seconds"]

                checkpoints = sample_route_polyline(
                    coordinates=coords,
                    total_duration_seconds=duration_sec,
                    departure_time=departure_time,
                    interval_miles=interval_miles,
                )

                # 4. Fetch weather for checkpoints at their specific ETA
                enriched_cps = enrich_checkpoints_with_weather(checkpoints)

                # 5. Evaluate pure risk function for each checkpoint
                for cp in enriched_cps:
                    w = cp["weather"]["wind_speed_mph"]
                    r = cp["weather"]["rain_in_hr"]
                    s = cp["weather"]["snow_in_hr"]

                    risk_result = calculate_checkpoint_risk(
                        wind_speed_mph=w,
                        rain_in_hr=r,
                        snow_in_hr=s,
                        load_weight_lb=load_weight,
                    )
                    cp["risk"] = risk_result.to_dict()

                route["checkpoints"] = enriched_cps

            # 6. Rank and recommend routes according to safety criteria
            ranked_routes = rank_and_recommend_routes(routes)

            # 7. Generate 48h corridor heatmap matrix (one payload for client slider)
            corridor_heatmap = get_corridor_48h_heatmap(
                routes=ranked_routes, load_weight_lb=load_weight
            )

            recommended_id = (
                ranked_routes[0]["id"] if ranked_routes else None
            )

            return Response(
                {
                    "origin": origin_info,
                    "destination": destination_info,
                    "departure_time": departure_time.isoformat(),
                    "load_weight_lb": load_weight,
                    "interval_miles": interval_miles,
                    "recommended_route_id": recommended_id,
                    "routes": ranked_routes,
                    "corridor_heatmap": corridor_heatmap,
                }
            )

        except ValueError as val_err:
            return Response({"error": str(val_err)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            logger.exception("Unexpected error analyzing routes")
            return Response(
                {"error": f"Internal server error analyzing routes: {str(exc)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
