"""
Weather Service using Open-Meteo API.

Fetches hourly wind speed (mph), precipitation (in/hr), and snowfall (in/hr)
for checkpoints along routes at their specific ETA hours.
Supports coordinate batching, caching, and resilient fallback handling.
"""

import math
import logging
import requests
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from django.core.cache import cache

logger = logging.getLogger(__name__)

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
BATCH_SIZE = 15  # Open-Meteo is most responsive with 15 coordinates per query


def parse_iso_datetime(dt_str: str) -> datetime:
    """Parse ISO string into UTC datetime."""
    # Remove trailing Z if present and parse
    clean_str = dt_str.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(clean_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        # Fallback to current UTC if parsing fails
        return datetime.now(timezone.utc)


def extract_weather_at_eta(
    hourly_data: Dict[str, Any], eta_dt: datetime
) -> Dict[str, float]:
    """
    Find the closest forecast hour to checkpoint ETA and extract weather variables.
    """
    times = hourly_data.get("time", [])
    wind_speeds = hourly_data.get("wind_speed_10m", [])
    precipitations = hourly_data.get("precipitation", [])
    snowfalls = hourly_data.get("snowfall", [])

    if not times:
        return {"wind_speed_mph": 8.0, "rain_in_hr": 0.0, "snow_in_hr": 0.0}

    best_idx = 0
    min_diff_seconds = float("inf")

    for idx, t_str in enumerate(times):
        try:
            # Open-Meteo hourly timestamps are formatted as "YYYY-MM-DDTHH:MM"
            t_dt = datetime.fromisoformat(t_str).replace(tzinfo=timezone.utc)
            diff = abs((t_dt - eta_dt).total_seconds())
            if diff < min_diff_seconds:
                min_diff_seconds = diff
                best_idx = idx
        except Exception:
            continue

    wind = float(wind_speeds[best_idx]) if best_idx < len(wind_speeds) and wind_speeds[best_idx] is not None else 5.0
    precip = float(precipitations[best_idx]) if best_idx < len(precipitations) and precipitations[best_idx] is not None else 0.0
    snow = float(snowfalls[best_idx]) if best_idx < len(snowfalls) and snowfalls[best_idx] is not None else 0.0

    # In meteorological terms, snowfall is snow rate (in/hr) and precipitation is total liquid.
    # If snow is falling, rain is residual liquid precipitation.
    if snow > 0:
        rain = max(0.0, precip - (snow * 0.1))
    else:
        rain = max(0.0, precip)

    return {
        "wind_speed_mph": round(wind, 1),
        "rain_in_hr": round(rain, 2),
        "snow_in_hr": round(snow, 2),
        "matched_forecast_time": times[best_idx] if best_idx < len(times) else "",
    }


def fetch_weather_batch(
    coords: List[Dict[str, float]], forecast_days: int = 4
) -> List[Optional[Dict[str, Any]]]:
    """
    Fetch weather for a batch of coordinates from Open-Meteo in resilient chunks.
    """
    if not coords:
        return []

    # If coordinates exceed BATCH_SIZE, fetch in small chunks to avoid server-side timeouts
    if len(coords) > BATCH_SIZE:
        all_results: List[Optional[Dict[str, Any]]] = []
        for i in range(0, len(coords), BATCH_SIZE):
            chunk = coords[i : i + BATCH_SIZE]
            all_results.extend(fetch_weather_batch(chunk, forecast_days=forecast_days))
        return all_results

    lat_str = ",".join(f"{c['latitude']:.4f}" for c in coords)
    lon_str = ",".join(f"{c['longitude']:.4f}" for c in coords)

    params = {
        "latitude": lat_str,
        "longitude": lon_str,
        "hourly": "wind_speed_10m,precipitation,snowfall",
        "wind_speed_unit": "mph",
        "precipitation_unit": "inch",
        "timezone": "UTC",
        "forecast_days": max(2, min(14, forecast_days)),
    }

    try:
        response = requests.get(OPEN_METEO_URL, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                return [item.get("hourly") for item in data]
            elif isinstance(data, dict):
                return [data.get("hourly")]
        else:
            logger.warning(f"Open-Meteo batch request failed with status {response.status_code}: {response.text}")
    except Exception as exc:
        logger.error(f"Error querying Open-Meteo batch: {exc}")

    return [None] * len(coords)


def enrich_checkpoints_with_weather(
    checkpoints: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Enrich each checkpoint with weather forecast matching its specific ETA.
    Uses caching and chunked batching.
    """
    if not checkpoints:
        return []

    # Check cache first for existing hourly forecasts
    results: List[Optional[Dict[str, Any]]] = [None] * len(checkpoints)
    missing_indices: List[int] = []

    for idx, cp in enumerate(checkpoints):
        eta_dt = parse_iso_datetime(cp["eta_iso"])
        date_str = eta_dt.strftime("%Y-%m-%d")
        cache_key = f"om_hourly_{cp['latitude']:.2f}_{cp['longitude']:.2f}_{date_str}"
        cached_hourly = cache.get(cache_key)

        if cached_hourly:
            results[idx] = cached_hourly
        else:
            missing_indices.append(idx)

    # Fetch missing coordinates in chunks
    if missing_indices:
        for i in range(0, len(missing_indices), BATCH_SIZE):
            chunk_indices = missing_indices[i : i + BATCH_SIZE]
            chunk_coords = [
                {
                    "latitude": checkpoints[idx]["latitude"],
                    "longitude": checkpoints[idx]["longitude"],
                }
                for idx in chunk_indices
            ]

            # Determine maximum days needed based on chunk ETAs
            now = datetime.now(timezone.utc)
            max_eta_days = 3
            for idx in chunk_indices:
                eta_dt = parse_iso_datetime(checkpoints[idx]["eta_iso"])
                days_ahead = (eta_dt - now).total_seconds() / 86400.0
                if days_ahead > max_eta_days:
                    max_eta_days = int(math.ceil(days_ahead)) + 1

            batch_hourly_list = fetch_weather_batch(chunk_coords, forecast_days=max_eta_days)

            for original_idx, hourly in zip(chunk_indices, batch_hourly_list):
                results[original_idx] = hourly
                if hourly:
                    cp = checkpoints[original_idx]
                    eta_dt = parse_iso_datetime(cp["eta_iso"])
                    date_str = eta_dt.strftime("%Y-%m-%d")
                    cache_key = f"om_hourly_{cp['latitude']:.2f}_{cp['longitude']:.2f}_{date_str}"
                    cache.set(cache_key, hourly, timeout=1800)

    # Extract checkpoint weather from hourly data
    enriched: List[Dict[str, Any]] = []
    for idx, cp in enumerate(checkpoints):
        cp_copy = dict(cp)
        eta_dt = parse_iso_datetime(cp["eta_iso"])
        hourly = results[idx]

        if hourly:
            weather_data = extract_weather_at_eta(hourly, eta_dt)
        else:
            # Fallback baseline weather if network error occurred
            weather_data = {
                "wind_speed_mph": 10.0,
                "rain_in_hr": 0.0,
                "snow_in_hr": 0.0,
                "matched_forecast_time": cp.get("eta_hour", ""),
            }

        cp_copy["weather"] = weather_data
        enriched.append(cp_copy)

    return enriched
