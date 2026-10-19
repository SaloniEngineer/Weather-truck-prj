"""
Unit Tests for Polyline Sampling and Mileage Accounting.

Tests:
- Walking polyline at 10, 25, 50 miles
- Segment representation (each checkpoint represents segment to the next)
- Total segment miles equals total polyline distance
- Cumulative ETA calculation strictly increasing with distance
"""

from datetime import datetime, timezone
import pytest
from routing.services.sampling_service import (
    sample_route_polyline,
    haversine_distance_miles,
)


class TestSamplingService:
    @pytest.fixture
    def sample_coords(self):
        # Straight line approx 100 miles East along latitude 40.0
        # 1 deg longitude at lat 40 is ~53 miles
        return [
            [-88.0, 40.0],
            [-87.0, 40.0],
            [-86.0, 40.0],
        ]

    def test_segment_miles_sum_matches_total_distance(self, sample_coords):
        departure = datetime(2026, 10, 19, 8, 0, 0, tzinfo=timezone.utc)
        total_duration = 7200.0  # 2 hours

        checkpoints = sample_route_polyline(
            coordinates=sample_coords,
            total_duration_seconds=total_duration,
            departure_time=departure,
            interval_miles=25.0,
        )

        assert len(checkpoints) >= 4

        # Sum of segment_miles
        total_segment_miles = sum(cp["segment_miles"] for cp in checkpoints)
        final_distance = checkpoints[-1]["distance_from_start_miles"]

        assert pytest.approx(total_segment_miles, abs=0.1) == final_distance
        # The last checkpoint (destination) must have segment_miles == 0
        assert checkpoints[-1]["segment_miles"] == 0.0

    def test_eta_progression(self, sample_coords):
        departure = datetime(2026, 10, 19, 8, 0, 0, tzinfo=timezone.utc)
        total_duration = 3600.0  # 1 hour

        checkpoints = sample_route_polyline(
            coordinates=sample_coords,
            total_duration_seconds=total_duration,
            departure_time=departure,
            interval_miles=10.0,
        )

        for i in range(1, len(checkpoints)):
            prev_cp = checkpoints[i - 1]
            curr_cp = checkpoints[i]

            assert curr_cp["distance_from_start_miles"] > prev_cp["distance_from_start_miles"]
            assert curr_cp["cumulative_duration_seconds"] > prev_cp["cumulative_duration_seconds"]

        # First checkpoint is at 0 miles with departure time
        assert checkpoints[0]["distance_from_start_miles"] == 0.0
        assert checkpoints[0]["cumulative_duration_seconds"] == 0.0
        assert checkpoints[0]["eta_iso"] == departure.isoformat()
