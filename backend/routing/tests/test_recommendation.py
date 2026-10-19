"""
Unit Tests for Route Recommendation Engine.

Tests:
- Ranking prefer order:
  1. No-travel excluded/deprioritized
  2. Fewest Severe miles
  3. Fewest High miles
  4. Lowest average risk
  5. Shortest travel times
- Proper badge assignment and 'why' explanation text
"""

import pytest
from routing.services.recommend_service import (
    evaluate_route_risk_profile,
    rank_and_recommend_routes,
)


class TestRecommendationEngine:
    def _create_mock_route(self, route_id, name, duration_sec, segments):
        # segments: list of (miles, risk_level, score)
        checkpoints = []
        cum_dist = 0.0
        for idx, (miles, level, score) in enumerate(segments):
            checkpoints.append({
                "index": idx,
                "distance_from_start_miles": cum_dist,
                "segment_miles": miles,
                "risk": {
                    "level": level,
                    "score": score,
                    "explanation": f"Test segment {idx}",
                }
            })
            cum_dist += miles

        return {
            "id": route_id,
            "name": name,
            "duration_seconds": duration_sec,
            "checkpoints": checkpoints,
        }

    def test_no_travel_route_is_deprioritized(self):
        # Route 1: Has 15 miles of No Travel, but is otherwise 1 hour faster
        r1 = self._create_mock_route(
            "r1", "Fast Route", 18000,
            [(15.0, "No Travel", 5), (100.0, "Low", 1)]
        )
        # Route 2: Safe route (0 No Travel, 20 Severe miles)
        r2 = self._create_mock_route(
            "r2", "Safe Route", 21600,
            [(20.0, "Severe", 4), (95.0, "Low", 1)]
        )

        ranked = rank_and_recommend_routes([r1, r2])
        assert ranked[0]["id"] == "r2"
        assert ranked[0]["is_recommended"] is True
        assert ranked[1]["id"] == "r1"
        assert ranked[1]["is_recommended"] is False
        assert "No-Travel" in ranked[1]["recommendation_why"]

    def test_fewest_severe_miles_preferred(self):
        # Both travelable, Route A has 10 severe miles, Route B has 40 severe miles
        r_a = self._create_mock_route(
            "ra", "Route A", 20000,
            [(10.0, "Severe", 4), (100.0, "Low", 1)]
        )
        r_b = self._create_mock_route(
            "rb", "Route B", 19000,
            [(40.0, "Severe", 4), (70.0, "Low", 1)]
        )

        ranked = rank_and_recommend_routes([r_a, r_b])
        assert ranked[0]["id"] == "ra"
        assert ranked[0]["is_recommended"] is True

    def test_fewest_high_miles_tiebreaker(self):
        # Equal Severe miles (0), but Route A has 15 High miles vs Route B has 35 High miles
        r_a = self._create_mock_route(
            "ra", "Route A", 20000,
            [(15.0, "High", 3), (100.0, "Low", 1)]
        )
        r_b = self._create_mock_route(
            "rb", "Route B", 19500,
            [(35.0, "High", 3), (80.0, "Low", 1)]
        )

        ranked = rank_and_recommend_routes([r_a, r_b])
        assert ranked[0]["id"] == "ra"
        assert ranked[0]["is_recommended"] is True

    def test_shortest_duration_tiebreaker(self):
        # Identical risk profiles, faster route wins
        r_fast = self._create_mock_route(
            "r_fast", "Fast Route", 18000,
            [(100.0, "Low", 1)]
        )
        r_slow = self._create_mock_route(
            "r_slow", "Slow Route", 21000,
            [(100.0, "Low", 1)]
        )

        ranked = rank_and_recommend_routes([r_slow, r_fast])
        assert ranked[0]["id"] == "r_fast"
        assert ranked[0]["is_recommended"] is True
