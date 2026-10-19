"""
Geocoding service for resolving origins and destinations to geographic coordinates.
Supports Nominatim OpenStreetMap API, direct lat/lon coordinate inputs, and local caching.
"""

import re
import logging
import requests
from typing import Optional, Tuple, Dict, Any
from django.core.cache import cache

logger = logging.getLogger(__name__)

# Fallback coordinates for common trucking hubs in case of rate limiting
COMMON_HUBS = {
    "chicago": (41.8781, -87.6298, "Chicago, IL, USA"),
    "chicago, il": (41.8781, -87.6298, "Chicago, IL, USA"),
    "denver": (39.7392, -104.9903, "Denver, CO, USA"),
    "denver, co": (39.7392, -104.9903, "Denver, CO, USA"),
    "dallas": (32.7767, -96.7970, "Dallas, TX, USA"),
    "dallas, tx": (32.7767, -96.7970, "Dallas, TX, USA"),
    "los angeles": (34.0522, -118.2437, "Los Angeles, CA, USA"),
    "los angeles, ca": (34.0522, -118.2437, "Los Angeles, CA, USA"),
    "seattle": (47.6062, -122.3321, "Seattle, WA, USA"),
    "seattle, wa": (47.6062, -122.3321, "Seattle, WA, USA"),
    "atlanta": (33.7490, -84.3880, "Atlanta, GA, USA"),
    "atlanta, ga": (33.7490, -84.3880, "Atlanta, GA, USA"),
    "new york": (40.7128, -74.0060, "New York, NY, USA"),
    "new york, ny": (40.7128, -74.0060, "New York, NY, USA"),
    "kansas city": (39.0997, -94.5786, "Kansas City, MO, USA"),
    "kansas city, mo": (39.0997, -94.5786, "Kansas City, MO, USA"),
    "salt lake city": (40.7608, -111.8910, "Salt Lake City, UT, USA"),
    "salt lake city, ut": (40.7608, -111.8910, "Salt Lake City, UT, USA"),
    "omaha": (41.2565, -95.9345, "Omaha, NE, USA"),
    "omaha, ne": (41.2565, -95.9345, "Omaha, NE, USA"),
}


def parse_direct_coordinates(query: str) -> Optional[Tuple[float, float, str]]:
    """Parse string if formatted as 'lat, lon'."""
    pattern = r"^\s*([+-]?\d+(?:\.\d+)?)\s*,\s*([+-]?\d+(?:\.\d+)?)\s*$"
    match = re.match(pattern, query)
    if match:
        lat = float(match.group(1))
        lon = float(match.group(2))
        if -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0:
            return lat, lon, f"Coordinates ({lat:.4f}, {lon:.4f})"
    return None


def geocode_location(query: str) -> Dict[str, Any]:
    """
    Resolve location query to {lat, lon, display_name}.
    Checks cache -> direct coords -> local hubs -> Nominatim OSM.
    """
    query_clean = query.strip()
    if not query_clean:
        raise ValueError("Location query cannot be empty.")

    safe_slug = re.sub(r'[^a-zA-Z0-9_]', '_', query_clean.lower())
    cache_key = f"geocode_{safe_slug}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    # Check direct coordinates
    direct = parse_direct_coordinates(query_clean)
    if direct:
        res = {"lat": direct[0], "lon": direct[1], "name": direct[2]}
        cache.set(cache_key, res, timeout=86400)
        return res

    # Check local common hubs
    key_norm = query_clean.lower()
    if key_norm in COMMON_HUBS:
        lat, lon, name = COMMON_HUBS[key_norm]
        res = {"lat": lat, "lon": lon, "name": name}
        cache.set(cache_key, res, timeout=86400)
        return res

    # Query OpenStreetMap Nominatim
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": query_clean,
        "format": "json",
        "limit": 1,
        "addressdetails": 1,
    }
    headers = {"User-Agent": "WeatherTruckRoutingApp/1.0 (truck-weather-routing)"}

    try:
        response = requests.get(url, params=params, headers=headers, timeout=8)
        if response.status_code == 200:
            results = response.json()
            if results and len(results) > 0:
                item = results[0]
                lat = float(item["lat"])
                lon = float(item["lon"])
                name = item.get("display_name", query_clean)
                res = {"lat": lat, "lon": lon, "name": name}
                cache.set(cache_key, res, timeout=86400)
                return res
    except Exception as exc:
        logger.warning(f"Nominatim geocoding failed for '{query_clean}': {exc}")

    # If Nominatim failed, check partial match in hubs
    for hub_name, (lat, lon, name) in COMMON_HUBS.items():
        if hub_name in key_norm:
            res = {"lat": lat, "lon": lon, "name": name}
            return res

    raise ValueError(f"Could not resolve coordinates for location: '{query_clean}'")
