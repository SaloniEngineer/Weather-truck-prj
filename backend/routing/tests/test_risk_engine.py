"""
Comprehensive Unit Tests for the Risk Assessment Engine.

Covers:
- Boundary conditions for wind, rain, and snow
- Strict half-open interval checks (e.g. 25.0, 34.5, 35.0, 45.0, 55.0)
- Compound weather condition prioritization (worst-condition rule)
- Truck load rules:
    - >= 55 mph -> No Travel for any load
    - 45–54 mph + >30,000 lb -> No Travel
    - 35–44 mph + >40,000 lb -> Severe
- Load escalation vs existing worst weather condition (no downgrades)
"""

import pytest
from routing.services.risk_service import (
    RiskLevel,
    calculate_checkpoint_risk,
    classify_rain_risk,
    classify_snow_risk,
    classify_wind_risk,
)


class TestWindRiskClassification:
    def test_low_wind(self):
        assert classify_wind_risk(0.0) == RiskLevel.LOW
        assert classify_wind_risk(15.0) == RiskLevel.LOW
        assert classify_wind_risk(24.99) == RiskLevel.LOW

    def test_moderate_wind_boundary(self):
        # 25.0 is the exact lower bound of Moderate [25, 35)
        assert classify_wind_risk(25.0) == RiskLevel.MODERATE
        # 34.5 is a common gap mistake in non-half-open implementations
        assert classify_wind_risk(34.5) == RiskLevel.MODERATE
        assert classify_wind_risk(34.99) == RiskLevel.MODERATE

    def test_high_wind_boundary(self):
        # 35.0 is the exact lower bound of High [35, 45)
        assert classify_wind_risk(35.0) == RiskLevel.HIGH
        assert classify_wind_risk(40.0) == RiskLevel.HIGH
        assert classify_wind_risk(44.99) == RiskLevel.HIGH

    def test_severe_wind_boundary(self):
        # 45.0 is the exact lower bound of Severe [45, 55)
        assert classify_wind_risk(45.0) == RiskLevel.SEVERE
        assert classify_wind_risk(50.0) == RiskLevel.SEVERE
        assert classify_wind_risk(54.99) == RiskLevel.SEVERE

    def test_no_travel_wind_boundary(self):
        # 55.0 is the exact lower bound of No Travel [55, inf)
        assert classify_wind_risk(55.0) == RiskLevel.NO_TRAVEL
        assert classify_wind_risk(65.0) == RiskLevel.NO_TRAVEL


class TestRainRiskClassification:
    def test_low_rain(self):
        assert classify_rain_risk(0.0) == RiskLevel.LOW
        assert classify_rain_risk(0.05) == RiskLevel.LOW
        assert classify_rain_risk(0.099) == RiskLevel.LOW

    def test_moderate_rain_boundary(self):
        assert classify_rain_risk(0.10) == RiskLevel.MODERATE
        assert classify_rain_risk(0.18) == RiskLevel.MODERATE
        assert classify_rain_risk(0.249) == RiskLevel.MODERATE

    def test_high_rain_boundary(self):
        assert classify_rain_risk(0.25) == RiskLevel.HIGH
        assert classify_rain_risk(0.35) == RiskLevel.HIGH
        assert classify_rain_risk(0.499) == RiskLevel.HIGH

    def test_severe_rain_boundary(self):
        assert classify_rain_risk(0.50) == RiskLevel.SEVERE
        assert classify_rain_risk(0.75) == RiskLevel.SEVERE
        assert classify_rain_risk(0.999) == RiskLevel.SEVERE

    def test_no_travel_rain_boundary(self):
        assert classify_rain_risk(1.00) == RiskLevel.NO_TRAVEL
        assert classify_rain_risk(1.50) == RiskLevel.NO_TRAVEL


class TestSnowRiskClassification:
    def test_low_snow(self):
        assert classify_snow_risk(0.0) == RiskLevel.LOW
        assert classify_snow_risk(0.25) == RiskLevel.LOW
        assert classify_snow_risk(0.499) == RiskLevel.LOW

    def test_moderate_snow_boundary(self):
        assert classify_snow_risk(0.50) == RiskLevel.MODERATE
        assert classify_snow_risk(0.75) == RiskLevel.MODERATE
        assert classify_snow_risk(0.999) == RiskLevel.MODERATE

    def test_high_snow_boundary(self):
        assert classify_snow_risk(1.00) == RiskLevel.HIGH
        assert classify_snow_risk(1.50) == RiskLevel.HIGH
        assert classify_snow_risk(1.999) == RiskLevel.HIGH

    def test_severe_snow_boundary(self):
        assert classify_snow_risk(2.00) == RiskLevel.SEVERE
        assert classify_snow_risk(2.50) == RiskLevel.SEVERE
        assert classify_snow_risk(2.999) == RiskLevel.SEVERE

    def test_no_travel_snow_boundary(self):
        assert classify_snow_risk(3.00) == RiskLevel.NO_TRAVEL
        assert classify_snow_risk(4.20) == RiskLevel.NO_TRAVEL


class TestCompoundRiskAndWorstCondition:
    def test_worst_condition_taken_rain_dominates(self):
        # Wind Low (15 mph), Rain Severe (0.60 in/hr), Snow Low (0.1 in/hr), standard load
        res = calculate_checkpoint_risk(
            wind_speed_mph=15.0,
            rain_in_hr=0.60,
            snow_in_hr=0.10,
            load_weight_lb=20000,
        )
        assert res.level == RiskLevel.SEVERE
        assert res.rain_risk == RiskLevel.SEVERE
        assert res.wind_risk == RiskLevel.LOW
        assert "Rain" in res.primary_hazard

    def test_worst_condition_taken_snow_dominates(self):
        # Wind Moderate (28 mph), Rain Low (0.05), Snow No Travel (3.5 in/hr)
        res = calculate_checkpoint_risk(
            wind_speed_mph=28.0,
            rain_in_hr=0.05,
            snow_in_hr=3.5,
            load_weight_lb=25000,
        )
        assert res.level == RiskLevel.NO_TRAVEL
        assert res.snow_risk == RiskLevel.NO_TRAVEL


class TestTruckLoadRules:
    def test_rule_1_extreme_wind_any_load(self):
        # >=55 mph -> No Travel for any load weight (even an empty or light truck)
        for load in [0, 5000, 20000, 30000, 45000, 80000]:
            res = calculate_checkpoint_risk(
                wind_speed_mph=55.0,
                rain_in_hr=0.0,
                snow_in_hr=0.0,
                load_weight_lb=load,
            )
            assert res.level == RiskLevel.NO_TRAVEL
            assert res.score == 5

    def test_rule_2_wind_45_54_with_load_threshold(self):
        # 45–54 mph + >30,000 lb -> No Travel
        # At exactly 30,000 lb (not strictly >30,000 lb), stays at Severe
        res_exact = calculate_checkpoint_risk(
            wind_speed_mph=48.0,
            rain_in_hr=0.0,
            snow_in_hr=0.0,
            load_weight_lb=30000.0,
        )
        assert res_exact.level == RiskLevel.SEVERE
        assert not res_exact.escalation_applied

        # At 30,001 lb (> 30,000 lb), escalates to No Travel
        res_over = calculate_checkpoint_risk(
            wind_speed_mph=48.0,
            rain_in_hr=0.0,
            snow_in_hr=0.0,
            load_weight_lb=30001.0,
        )
        assert res_over.level == RiskLevel.NO_TRAVEL
        assert res_over.escalation_applied
        assert "rollover risk" in res_over.explanation

    def test_rule_3_wind_35_44_with_load_threshold(self):
        # 35–44 mph + >40,000 lb -> Severe
        # At exactly 40,000 lb, stays High
        res_exact = calculate_checkpoint_risk(
            wind_speed_mph=40.0,
            rain_in_hr=0.0,
            snow_in_hr=0.0,
            load_weight_lb=40000.0,
        )
        assert res_exact.level == RiskLevel.HIGH
        assert not res_exact.escalation_applied

        # At 40,001 lb (> 40,000 lb), escalates to Severe
        res_over = calculate_checkpoint_risk(
            wind_speed_mph=40.0,
            rain_in_hr=0.0,
            snow_in_hr=0.0,
            load_weight_lb=40001.0,
        )
        assert res_over.level == RiskLevel.SEVERE
        assert res_over.escalation_applied
        assert "over 40,000 lb" in res_over.explanation

    def test_load_rule_does_not_downgrade_higher_weather_risk(self):
        # Suppose rain is No Travel (1.2 in/hr), but wind is 38 mph with load 45,000 lb
        # Load rule alone would evaluate to Severe, but rain is No Travel.
        # Result must remain No Travel!
        res = calculate_checkpoint_risk(
            wind_speed_mph=38.0,
            rain_in_hr=1.20,
            snow_in_hr=0.0,
            load_weight_lb=45000.0,
        )
        assert res.level == RiskLevel.NO_TRAVEL
        assert res.score == 5
