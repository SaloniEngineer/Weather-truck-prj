"""
Route Recommendation and Evaluation Engine.

Evaluates route options against weather risk criteria and ranks them strictly according to:
1. Feasibility (exclude or deprioritize routes with No Travel segments)
2. Fewest Severe miles
3. Fewest High miles
4. Lowest mileage-weighted average risk score
5. Shortest travel time

Generates clear, human-understandable recommendation rationale ('why') and badge metadata.
"""

from typing import List, Dict, Any, Tuple
from routing.services.risk_service import RiskLevel


def format_duration(seconds: float) -> str:
    """Format duration in seconds to 'Xh Ym'."""
    hrs = int(seconds // 3600)
    mins = int(round((seconds % 3600) / 60))
    if hrs == 0:
        return f"{mins}m"
    return f"{hrs}h {mins:02d}m"


def evaluate_route_risk_profile(route: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compute aggregate risk miles, safety feasibility, and weighted average risk for a route.
    """
    checkpoints = route.get("checkpoints", [])
    total_miles = 0.0
    no_travel_miles = 0.0
    severe_miles = 0.0
    high_miles = 0.0
    moderate_miles = 0.0
    low_miles = 0.0
    weighted_score_sum = 0.0

    for cp in checkpoints:
        seg_miles = float(cp.get("segment_miles", 0.0))
        risk_data = cp.get("risk", {})
        risk_level = risk_data.get("level", RiskLevel.LOW.value)
        risk_score = int(risk_data.get("score", 1))

        total_miles += seg_miles
        weighted_score_sum += seg_miles * risk_score

        if risk_level == RiskLevel.NO_TRAVEL.value:
            no_travel_miles += seg_miles
        elif risk_level == RiskLevel.SEVERE.value:
            severe_miles += seg_miles
        elif risk_level == RiskLevel.HIGH.value:
            high_miles += seg_miles
        elif risk_level == RiskLevel.MODERATE.value:
            moderate_miles += seg_miles
        else:
            low_miles += seg_miles

    avg_risk_score = (
        round(weighted_score_sum / total_miles, 2) if total_miles > 0 else 1.0
    )

    is_travelable = (no_travel_miles == 0.0)

    # Determine predominant route risk category
    if no_travel_miles > 0:
        overall_level = RiskLevel.NO_TRAVEL.value
    elif severe_miles > 0:
        overall_level = RiskLevel.SEVERE.value
    elif high_miles > 0:
        overall_level = RiskLevel.HIGH.value
    elif moderate_miles > 0:
        overall_level = RiskLevel.MODERATE.value
    else:
        overall_level = RiskLevel.LOW.value

    return {
        "total_miles": round(total_miles, 1),
        "no_travel_miles": round(no_travel_miles, 1),
        "severe_miles": round(severe_miles, 1),
        "high_miles": round(high_miles, 1),
        "moderate_miles": round(moderate_miles, 1),
        "low_miles": round(low_miles, 1),
        "avg_risk_score": avg_risk_score,
        "is_travelable": is_travelable,
        "overall_risk_level": overall_level,
    }


def rank_and_recommend_routes(routes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Rank routes using multi-attribute safety optimization:
    1. Feasible routes (0 No-Travel miles) first; if none, fewest No-Travel miles
    2. Fewest Severe miles
    3. Fewest High miles
    4. Lowest mileage-weighted average risk
    5. Shortest travel time
    """
    if not routes:
        return []

    # First attach evaluated profile to each route
    evaluated_routes: List[Dict[str, Any]] = []
    for r in routes:
        r_copy = dict(r)
        profile = evaluate_route_risk_profile(r_copy)
        r_copy["risk_profile"] = profile
        evaluated_routes.append(r_copy)

    # Sorting key tuple:
    # 0: not travelable (False comes before True)
    # 1: no_travel_miles
    # 2: severe_miles
    # 3: high_miles
    # 4: avg_risk_score
    # 5: duration_seconds
    def sorting_key(route: Dict[str, Any]) -> Tuple:
        p = route["risk_profile"]
        duration = float(route.get("duration_seconds", 0.0))
        return (
            not p["is_travelable"],
            p["no_travel_miles"],
            p["severe_miles"],
            p["high_miles"],
            p["avg_risk_score"],
            duration,
        )

    ranked = sorted(evaluated_routes, key=sorting_key)

    # Decorate with recommendation badge and explanation ("why")
    recommended = ranked[0]
    rec_prof = recommended["risk_profile"]
    rec_duration = recommended.get("duration_seconds", 0.0)

    for idx, r in enumerate(ranked):
        p = r["risk_profile"]
        duration = r.get("duration_seconds", 0.0)
        time_diff = duration - rec_duration

        if idx == 0:
            r["is_recommended"] = True
            r["rank"] = 1

            # Build clear, convincing rationale
            reasons = []
            if rec_prof["no_travel_miles"] == 0:
                reasons.append("0 No-Travel miles")
            else:
                reasons.append(f"Lowest hazardous exposure ({rec_prof['no_travel_miles']} mi No-Travel)")

            reasons.append(f"{rec_prof['severe_miles']:.0f} Severe miles")

            if rec_prof["high_miles"] > 0:
                reasons.append(f"{rec_prof['high_miles']:.0f} High miles")

            why_text = f"Top safety choice: {', '.join(reasons)}."
            if len(ranked) > 1:
                other_severe = [o["risk_profile"]["severe_miles"] for o in ranked[1:]]
                max_other_sev = max(other_severe) if other_severe else 0
                if max_other_sev > rec_prof["severe_miles"]:
                    saved_sev = max_other_sev - rec_prof["severe_miles"]
                    why_text += f" Avoids {saved_sev:.0f} miles of severe storm conditions compared to alternatives."

            r["recommendation_why"] = why_text
            r["badge"] = "★ RECOMMENDED"
        else:
            r["is_recommended"] = False
            r["rank"] = idx + 1
            r["badge"] = f"Option {idx + 1}"

            # Explain trade-off compared to recommended
            parts = []
            if not p["is_travelable"]:
                parts.append(f"Hazardous: {p['no_travel_miles']:.0f} mi No-Travel (unsafe)")
            elif p["severe_miles"] > rec_prof["severe_miles"]:
                parts.append(f"+{p['severe_miles'] - rec_prof['severe_miles']:.0f} more Severe miles")
            elif p["high_miles"] > rec_prof["high_miles"]:
                parts.append(f"+{p['high_miles'] - rec_prof['high_miles']:.0f} more High miles")

            if time_diff < -60:
                parts.append(f"{format_duration(abs(time_diff))} faster but higher weather risk")
            elif time_diff > 60:
                parts.append(f"{format_duration(time_diff)} slower")

            r["recommendation_why"] = "; ".join(parts) if parts else "Alternative route"

    return ranked
