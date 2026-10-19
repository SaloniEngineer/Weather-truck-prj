"""
Risk Assessment Engine for Weather-Aware Truck Routing.

Calculates risk level per checkpoint based on weather conditions (wind speed,
rain rate, snow rate) and truck cargo load rules using strict half-open intervals.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class RiskLevel(str, Enum):
    LOW = "Low"
    MODERATE = "Moderate"
    HIGH = "High"
    SEVERE = "Severe"
    NO_TRAVEL = "No Travel"

    @property
    def score(self) -> int:
        """Numeric rank for sorting, averaging, and comparison."""
        mapping = {
            RiskLevel.LOW: 1,
            RiskLevel.MODERATE: 2,
            RiskLevel.HIGH: 3,
            RiskLevel.SEVERE: 4,
            RiskLevel.NO_TRAVEL: 5,
        }
        return mapping[self]

    @property
    def color(self) -> str:
        """Standard UI color code."""
        mapping = {
            RiskLevel.LOW: "#22c55e",       # Green
            RiskLevel.MODERATE: "#eab308",  # Yellow
            RiskLevel.HIGH: "#f97316",      # Orange
            RiskLevel.SEVERE: "#ef4444",    # Red
            RiskLevel.NO_TRAVEL: "#1f2937", # Dark slate / Black
        }
        return mapping[self]


@dataclass(frozen=True)
class CheckpointRiskResult:
    level: RiskLevel
    score: int
    wind_risk: RiskLevel
    rain_risk: RiskLevel
    snow_risk: RiskLevel
    escalation_applied: bool
    primary_hazard: str
    explanation: str

    def to_dict(self) -> dict:
        return {
            "level": self.level.value,
            "score": self.score,
            "wind_risk": self.wind_risk.value,
            "rain_risk": self.rain_risk.value,
            "snow_risk": self.snow_risk.value,
            "escalation_applied": self.escalation_applied,
            "primary_hazard": self.primary_hazard,
            "explanation": self.explanation,
            "color": self.level.color,
        }


def classify_wind_risk(wind_mph: float) -> RiskLevel:
    """
    Classify wind speed (mph) using half-open intervals:
    - [0, 25)    -> Low
    - [25, 35)   -> Moderate
    - [35, 45)   -> High
    - [45, 55)   -> Severe
    - [55, inf)  -> No Travel
    """
    if wind_mph < 25.0:
        return RiskLevel.LOW
    elif wind_mph < 35.0:
        return RiskLevel.MODERATE
    elif wind_mph < 45.0:
        return RiskLevel.HIGH
    elif wind_mph < 55.0:
        return RiskLevel.SEVERE
    else:
        return RiskLevel.NO_TRAVEL


def classify_rain_risk(rain_in_hr: float) -> RiskLevel:
    """
    Classify rain rate (inches/hour) using half-open intervals:
    - [0, 0.10)   -> Low
    - [0.10, 0.25) -> Moderate
    - [0.25, 0.50) -> High
    - [0.50, 1.00) -> Severe
    - [1.00, inf)  -> No Travel
    """
    if rain_in_hr < 0.10:
        return RiskLevel.LOW
    elif rain_in_hr < 0.25:
        return RiskLevel.MODERATE
    elif rain_in_hr < 0.50:
        return RiskLevel.HIGH
    elif rain_in_hr < 1.00:
        return RiskLevel.SEVERE
    else:
        return RiskLevel.NO_TRAVEL


def classify_snow_risk(snow_in_hr: float) -> RiskLevel:
    """
    Classify snowfall rate (inches/hour) using half-open intervals:
    - [0, 0.50)   -> Low
    - [0.50, 1.00) -> Moderate
    - [1.00, 2.00) -> High
    - [2.00, 3.00) -> Severe
    - [3.00, inf)  -> No Travel
    """
    if snow_in_hr < 0.50:
        return RiskLevel.LOW
    elif snow_in_hr < 1.00:
        return RiskLevel.MODERATE
    elif snow_in_hr < 2.00:
        return RiskLevel.HIGH
    elif snow_in_hr < 3.00:
        return RiskLevel.SEVERE
    else:
        return RiskLevel.NO_TRAVEL


def calculate_checkpoint_risk(
    wind_speed_mph: float,
    rain_in_hr: float,
    snow_in_hr: float,
    load_weight_lb: float,
) -> CheckpointRiskResult:
    """
    Pure function evaluating overall risk for a checkpoint.

    Steps:
    1. Evaluate base risk for wind, rain, and snow using continuous half-open intervals.
    2. Determine base risk level as the maximum (worst) among individual conditions.
    3. Apply cargo load rules:
       - wind >= 55 mph -> No Travel for any load
       - 45 <= wind < 55 mph + load > 30,000 lb -> No Travel
       - 35 <= wind < 45 mph + load > 40,000 lb -> Severe (escalated)
    """
    # Guard negative values cleanly
    wind = max(0.0, float(wind_speed_mph))
    rain = max(0.0, float(rain_in_hr))
    snow = max(0.0, float(snow_in_hr))
    load = max(0.0, float(load_weight_lb))

    w_risk = classify_wind_risk(wind)
    r_risk = classify_rain_risk(rain)
    s_risk = classify_snow_risk(snow)

    # Base worst condition
    ranked = sorted(
        [
            (w_risk, f"Wind ({wind:.1f} mph)"),
            (r_risk, f"Rain ({rain:.2f} in/hr)"),
            (s_risk, f"Snow ({snow:.2f} in/hr)"),
        ],
        key=lambda pair: pair[0].score,
        reverse=True,
    )

    base_risk, primary_hazard = ranked[0]
    final_risk = base_risk
    escalation_applied = False
    explanation_parts = []

    # Check Load Rules (PDF page 2)
    # Rule 1: >=55 mph -> No Travel for any load
    if wind >= 55.0:
        final_risk = RiskLevel.NO_TRAVEL
        primary_hazard = f"Extreme wind ({wind:.1f} mph)"
        explanation_parts.append(f"Dangerous wind speeds >= 55 mph mandate No Travel for any load weight.")

    # Rule 2: 45–54 mph + >30,000 lb -> No Travel
    elif 45.0 <= wind < 55.0 and load > 30000.0:
        if final_risk.score < RiskLevel.NO_TRAVEL.score:
            final_risk = RiskLevel.NO_TRAVEL
            escalation_applied = True
            primary_hazard = f"High wind ({wind:.1f} mph) with heavy load ({load:,.0f} lb)"
            explanation_parts.append(
                f"Sustained wind of {wind:.1f} mph with load over 30,000 lb ({load:,.0f} lb) creates severe rollover risk: No Travel."
            )

    # Rule 3: 35–44 mph + >40,000 lb -> Severe
    elif 35.0 <= wind < 45.0 and load > 40000.0:
        if final_risk.score < RiskLevel.SEVERE.score:
            final_risk = RiskLevel.SEVERE
            escalation_applied = True
            primary_hazard = f"Moderate/High wind ({wind:.1f} mph) with heavy load ({load:,.0f} lb)"
            explanation_parts.append(
                f"Crosswind of {wind:.1f} mph with load over 40,000 lb ({load:,.0f} lb) escalates condition to Severe."
            )

    if not explanation_parts:
        if final_risk == RiskLevel.LOW:
            explanation = "Clear travel conditions within safe operating limits."
        else:
            explanation = f"{primary_hazard} determines checkpoint risk as {final_risk.value}."
    else:
        explanation = " ".join(explanation_parts)

    return CheckpointRiskResult(
        level=final_risk,
        score=final_risk.score,
        wind_risk=w_risk,
        rain_risk=r_risk,
        snow_risk=s_risk,
        escalation_applied=escalation_applied,
        primary_hazard=primary_hazard,
        explanation=explanation,
    )
