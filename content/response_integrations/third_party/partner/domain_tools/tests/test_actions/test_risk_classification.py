from __future__ import annotations

import pytest

from domain_tools.core.constants import (
    RISK_CATEGORY_HIGH,
    RISK_CATEGORY_LOW,
    RISK_CATEGORY_MEDIUM,
    RISK_CATEGORY_SUSPICIOUS,
    RISK_CATEGORY_YOUNG,
)
from domain_tools.core.UtilsManager import classify_domain_risk


class TestClassifyDomainRisk:
    """Unit tests for classify_domain_risk() — no mocking needed."""

    def test_high_risk(self):
        assert classify_domain_risk(87, 365) == RISK_CATEGORY_HIGH

    def test_high_risk_boundary(self):
        assert classify_domain_risk(70, 365) == RISK_CATEGORY_HIGH

    def test_medium_risk(self):
        assert classify_domain_risk(55, 365) == RISK_CATEGORY_MEDIUM

    def test_medium_risk_boundary(self):
        assert classify_domain_risk(40, 365) == RISK_CATEGORY_MEDIUM

    def test_suspicious(self):
        assert classify_domain_risk(30, 365) == RISK_CATEGORY_SUSPICIOUS

    def test_suspicious_boundary(self):
        assert classify_domain_risk(20, 365) == RISK_CATEGORY_SUSPICIOUS

    def test_low_risk(self):
        assert classify_domain_risk(5, 365) == RISK_CATEGORY_LOW

    def test_low_risk_zero(self):
        assert classify_domain_risk(0, 365) == RISK_CATEGORY_LOW

    def test_young_domain_takes_precedence_over_high_risk(self):
        # A high-risk score but newly registered — young_domain wins
        assert classify_domain_risk(85, 5) == RISK_CATEGORY_YOUNG

    def test_young_domain_boundary(self):
        assert classify_domain_risk(10, 29) == RISK_CATEGORY_YOUNG

    def test_not_young_domain_at_boundary(self):
        # Exactly 30 days — no longer young
        assert classify_domain_risk(10, 30) == RISK_CATEGORY_LOW

    def test_young_domain_with_low_score(self):
        assert classify_domain_risk(5, 1) == RISK_CATEGORY_YOUNG

    def test_unknown_age_falls_back_to_score(self):
        # age_days=None means age is unknown — classify by score only
        assert classify_domain_risk(85, None) == RISK_CATEGORY_HIGH
        assert classify_domain_risk(5, None) == RISK_CATEGORY_LOW
