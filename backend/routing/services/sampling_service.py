"""
Polyline Sampling Service.

Walks the route polyline at specified distance intervals (10, 25, 50 miles)
and calculates checkpoint coordinates, cumulative distance, segment length,
and accurate Estimated Time of Arrival (ETA) based on departure time and travel duration.
"""

import math
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple


EARTH_RADIUS_MILES = 3958.7613  # Mean Earth radius in miles


def haversine_distance_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two points in miles."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return EARTH_RADIUS_MILES * c


def interpolate_point(
    lat1: float, lon1: float, lat2: float, lon2: float, fraction: float
) -> Tuple[float, float]:
    """Linearly interpolate between two coordinates."""
    fraction = max(0.0, min(1.0, fraction))
    lat = lat1 + (lat2 - lat1) * fraction
    lon = lon1 + (lon2 - lon1) * fraction
    return lat, lon


def sample_route_polyline(
    coordinates: List[List[float]],
    total_duration_seconds: float,
    departure_time: datetime,
    interval_miles: float = 25.0,
) -> List[Dict[str, Any]]:
    """
    Sample route coordinates every `interval_miles` (e.g. 10, 25, 50 miles).

    Args:
        coordinates: List of [lon, lat] coordinates representing the full route polyline.
        total_duration_seconds: Total driving time for the route.
        departure_time: Departure datetime (timezone aware or UTC).
        interval_miles: Sampling step in miles (10, 25, 50).

    Returns:
        List of checkpoint dicts, where each checkpoint represents the segment
        to the next checkpoint. The sum of all segment_miles equals the total route distance.
    """
    if not coordinates or len(coordinates) < 2:
        raise ValueError("Route polyline must have at least 2 coordinate points.")

    interval_miles = float(interval_miles)
    if interval_miles <= 0:
        interval_miles = 25.0

    # 1. Compute cumulative distances along the raw polyline points
    # coordinates are [lon, lat]
    poly_points: List[Tuple[float, float]] = [(pt[1], pt[0]) for pt in coordinates]  # (lat, lon)
    cum_dists: List[float] = [0.0]

    for i in range(1, len(poly_points)):
        p1 = poly_points[i - 1]
        p2 = poly_points[i]
        d = haversine_distance_miles(p1[0], p1[1], p2[0], p2[1])
        cum_dists.append(cum_dists[-1] + d)

    total_dist_miles = cum_dists[-1]

    # 2. Determine target distances for checkpoints: 0, interval, 2*interval... and destination
    target_dists: List[float] = [0.0]
    curr = interval_miles
    while curr < total_dist_miles:
        # Don't add if it's virtually at the destination (< 1.5 miles from end)
        if total_dist_miles - curr >= 1.5:
            target_dists.append(curr)
        curr += interval_miles

    # Always include the destination endpoint
    if total_dist_miles > target_dists[-1]:
        target_dists.append(total_dist_miles)

    # 3. Interpolate coordinates at each target distance
    sampled_checkpoints: List[Dict[str, Any]] = []
    seg_idx = 0

    for idx, target_d in enumerate(target_dists):
        # Find segment in raw polyline containing target_d
        while seg_idx < len(cum_dists) - 2 and cum_dists[seg_idx + 1] < target_d:
            seg_idx += 1

        p1 = poly_points[seg_idx]
        p2 = poly_points[seg_idx + 1]
        d1 = cum_dists[seg_idx]
        d2 = cum_dists[seg_idx + 1]
        seg_len = d2 - d1

        if seg_len > 1e-6:
            frac = (target_d - d1) / seg_len
            lat, lon = interpolate_point(p1[0], p1[1], p2[0], p2[1], frac)
        else:
            lat, lon = p1

        # Calculate ETA based on cumulative distance fraction
        fraction_of_route = target_d / total_dist_miles if total_dist_miles > 0 else 0.0
        elapsed_seconds = fraction_of_route * total_duration_seconds
        checkpoint_eta = departure_time + timedelta(seconds=elapsed_seconds)

        sampled_checkpoints.append(
            {
                "index": idx,
                "latitude": round(lat, 5),
                "longitude": round(lon, 5),
                "distance_from_start_miles": round(target_d, 2),
                "cumulative_duration_seconds": round(elapsed_seconds, 1),
                "eta_iso": checkpoint_eta.isoformat(),
                "eta_hour": checkpoint_eta.strftime("%Y-%m-%dT%H:00:00Z"),
                "is_destination": idx == len(target_dists) - 1,
            }
        )

    # 4. Assign segment_miles: Each checkpoint represents the segment to the next one
    for idx in range(len(sampled_checkpoints)):
        if idx < len(sampled_checkpoints) - 1:
            seg_miles = (
                sampled_checkpoints[idx + 1]["distance_from_start_miles"]
                - sampled_checkpoints[idx]["distance_from_start_miles"]
            )
            sampled_checkpoints[idx]["segment_miles"] = round(seg_miles, 2)
        else:
            # Last checkpoint is the final destination
            sampled_checkpoints[idx]["segment_miles"] = 0.0

    return sampled_checkpoints
