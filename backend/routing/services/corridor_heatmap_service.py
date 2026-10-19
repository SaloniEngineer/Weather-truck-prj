"""
Corridor Weather Heatmap Service.

Fetches 48 hours of hourly forecast data once for a representative grid of points
along the travel corridor. Returns the entire 48h temporal dataset in a single compact
payload so the client slider can smoothly scrub through hours with 0ms latency and no refetching.
"""

import math
import logging
from typing import List, Dict, Any, Tuple
from django.core.cache import cache

from routing.services.risk_service import calculate_checkpoint_risk
from routing.services.weather_service import fetch_weather_batch

logger = logging.getLogger(__name__)


def generate_corridor_grid(
    routes: List[Dict[str, Any]], max_points: int = 20
) -> List[Tuple[float, float]]:
    """
    Generate an evenly distributed set of corridor points covering all route geometries.
    """
    all_coords: List[Tuple[float, float]] = []
    for route in routes:
        # Checkpoints or geometry coords
        checkpoints = route.get("checkpoints", [])
        if checkpoints:
            for cp in checkpoints:
                all_coords.append((cp["latitude"], cp["longitude"]))
        else:
            # Fallback to route geometry
            geom = route.get("geometry", {}).get("coordinates", [])
            for pt in geom:
                all_coords.append((pt[1], pt[0]))

    if not all_coords:
        return []

    # Filter/subsample to approximately max_points evenly spaced coordinates
    step = max(1, len(all_coords) // max_points)
    sampled = all_coords[::step][:max_points]

    # Also add bounding box corner/mid points to give spatial depth
    lats = [c[0] for c in all_coords]
    lons = [c[1] for c in all_coords]
    min_lat, max_lat = min(lats), max(lats)
    min_lon, max_lon = min(lons), max(lons)

    # Add midpoint corridor extensions for smoother spatial interpolation
    mid_lat = (min_lat + max_lat) / 2.0
    mid_lon = (min_lon + max_lon) / 2.0
    sampled.append((round(mid_lat, 4), round(mid_lon, 4)))

    # Deduplicate within ~0.3 degrees (~20 miles)
    unique_points: List[Tuple[float, float]] = []
    for lat, lon in sampled:
        lat_r, lon_r = round(lat, 2), round(lon, 2)
        if not any(abs(lat_r - u[0]) < 0.25 and abs(lon_r - u[1]) < 0.25 for u in unique_points):
            unique_points.append((lat_r, lon_r))

    return unique_points[:max_points]


def get_corridor_48h_heatmap(
    routes: List[Dict[str, Any]], load_weight_lb: float = 30000.0
) -> Dict[str, Any]:
    """
    Fetch 48 hours of hourly weather once for corridor points.
    Returns 48-hour time series for each point.
    """
    corridor_points = generate_corridor_grid(routes, max_points=20)
    if not corridor_points:
        return {"timestamps": [], "hours_count": 0, "points": []}

    # Prepare coordinate list for batch call
    coord_payload = [
        {"latitude": pt[0], "longitude": pt[1]} for pt in corridor_points
    ]

    # Batch request 48 hours (2 days)
    hourly_results = fetch_weather_batch(coord_payload, forecast_days=2)

    # Find the common timestamps array (up to 48 hours)
    common_timestamps: List[str] = []
    for h in hourly_results:
        if h and "time" in h and len(h["time"]) >= 48:
            common_timestamps = h["time"][:48]
            break

    if not common_timestamps and hourly_results and hourly_results[0] and "time" in hourly_results[0]:
        common_timestamps = hourly_results[0]["time"]

    hours_count = min(48, len(common_timestamps))
    common_timestamps = common_timestamps[:hours_count]

    # Process each point's 48-hour time series
    processed_points: List[Dict[str, Any]] = []

    for idx, (lat, lon) in enumerate(corridor_points):
        hourly = hourly_results[idx] if idx < len(hourly_results) else None

        wind_series: List[float] = []
        rain_series: List[float] = []
        snow_series: List[float] = []
        risk_level_series: List[str] = []
        risk_score_series: List[int] = []

        if hourly:
            w_list = hourly.get("wind_speed_10m", [])
            p_list = hourly.get("precipitation", [])
            s_list = hourly.get("snowfall", [])

            for h_idx in range(hours_count):
                w = float(w_list[h_idx]) if h_idx < len(w_list) and w_list[h_idx] is not None else 8.0
                p = float(p_list[h_idx]) if h_idx < len(p_list) and p_list[h_idx] is not None else 0.0
                s = float(s_list[h_idx]) if h_idx < len(s_list) and s_list[h_idx] is not None else 0.0
                r = max(0.0, p - (s * 0.1)) if s > 0 else max(0.0, p)

                risk_res = calculate_checkpoint_risk(w, r, s, load_weight_lb)

                wind_series.append(round(w, 1))
                rain_series.append(round(r, 2))
                snow_series.append(round(s, 2))
                risk_level_series.append(risk_res.level.value)
                risk_score_series.append(risk_res.score)
        else:
            # Fallback default benign weather
            for _ in range(hours_count):
                wind_series.append(7.0)
                rain_series.append(0.0)
                snow_series.append(0.0)
                risk_level_series.append("Low")
                risk_score_series.append(1)

        processed_points.append(
            {
                "lat": lat,
                "lon": lon,
                "wind": wind_series,
                "rain": rain_series,
                "snow": snow_series,
                "risk_level": risk_level_series,
                "risk_score": risk_score_series,
            }
        )

    return {
        "hours_count": hours_count,
        "timestamps": common_timestamps,
        "points": processed_points,
    }
