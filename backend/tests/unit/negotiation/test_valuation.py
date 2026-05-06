"""
Unit tests for NeutralEngine._compute_valuation() — Valuation Context Starvation fix.

Tests verify that:
1. When RFQ parsed_fields + catalogue_price are available, intrinsic value is used
2. When RFQ data is missing, budget_ceiling fallback is used
3. Real-world scenario: 600 Kg @ ₹75/kg produces valuations near ₹45,000 (not ₹8L)
"""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest

from src.negotiation.domain.agent_profile import AgentProfile
from src.negotiation.domain.value_objects import RiskProfile, StrategyWeights
from src.negotiation.infrastructure.neutral_engine import NeutralEngine


def _make_profile(
    budget_ceiling: Decimal = Decimal("1000000"),
    margin_floor: Decimal = Decimal("10"),
    risk_appetite: str = "MEDIUM",
) -> AgentProfile:
    """Create an AgentProfile with the given risk parameters."""
    return AgentProfile(
        enterprise_id=uuid.uuid4(),
        risk_profile=RiskProfile(
            budget_ceiling=budget_ceiling,
            margin_floor=margin_floor,
            risk_appetite=risk_appetite,
        ),
        strategy_weights=StrategyWeights(),
    )


def _make_engine() -> NeutralEngine:
    """Create a NeutralEngine with a stub agent driver."""
    return NeutralEngine(agent_driver=None)


# ─── Test 1: Intrinsic value path — buyer ────────────────────────────────────


class TestComputeValuationIntrinsicPath:
    """_compute_valuation uses RFQ+catalogue data when available."""

    def test_buyer_uses_rfq_budget_range(self) -> None:
        """Buyer valuation derived from budget_min/budget_max, not budget_ceiling."""
        engine = _make_engine()
        profile = _make_profile(budget_ceiling=Decimal("1000000"))

        rfq_fields = {
            "quantity": 600,
            "unit_rate": 75,
            "budget_min": 40000,
            "budget_max": 50000,
        }

        val = engine._compute_valuation(
            profile, is_buyer=True,
            rfq_parsed_fields=rfq_fields,
            catalogue_price=Decimal("70"),
        )

        # Fair price = midpoint of 40000-50000 = 45000
        # Target should be near 45000 (with MEDIUM discount), NOT near 800000
        assert val.target_price < Decimal("50000"), (
            f"Buyer target_price {val.target_price} should be < ₹50,000 "
            f"(derived from RFQ budget range), not from ₹10L ceiling"
        )
        assert val.reservation_price <= Decimal("50000"), (
            f"Buyer reservation_price {val.reservation_price} should be <= ₹50,000"
        )

    def test_buyer_uses_intrinsic_when_no_budget_range(self) -> None:
        """Buyer valuation uses intrinsic_value when budget_min/max missing."""
        engine = _make_engine()
        profile = _make_profile(budget_ceiling=Decimal("1000000"))

        rfq_fields = {
            "quantity": 600,
            "unit_rate": 75,
            # No budget_min/budget_max
        }

        val = engine._compute_valuation(
            profile, is_buyer=True,
            rfq_parsed_fields=rfq_fields,
            catalogue_price=None,
        )

        # Intrinsic = 600 × 75 = 45000 → fair_price = 45000
        # Target should be near 45000, NOT near 800000
        assert val.target_price < Decimal("60000"), (
            f"Buyer target_price {val.target_price} should be derived from "
            f"intrinsic ₹45,000, not from ₹10L ceiling"
        )

    def test_seller_uses_catalogue_price(self) -> None:
        """Seller valuation derived from catalogue_price, not budget_ceiling × 0.60."""
        engine = _make_engine()
        profile = _make_profile(
            budget_ceiling=Decimal("1000000"),
            margin_floor=Decimal("10"),
        )

        rfq_fields = {
            "quantity": 600,
            "unit_rate": 75,
        }

        val = engine._compute_valuation(
            profile, is_buyer=False,
            rfq_parsed_fields=rfq_fields,
            catalogue_price=Decimal("70"),  # ₹70/unit cost basis
        )

        # Seller cost_basis = catalogue_price = ₹70
        # reservation = 70 × 1.10 = ₹77, target = 70 × 1.20 = ₹84
        # NOT ₹600,000 × 1.10 = ₹660,000
        assert val.reservation_price < Decimal("200"), (
            f"Seller reservation_price {val.reservation_price} should be derived from "
            f"catalogue_price ₹70, not from ₹10L × 0.60"
        )

    def test_seller_falls_back_to_intrinsic_without_catalogue(self) -> None:
        """Seller uses intrinsic_value when catalogue_price is None."""
        engine = _make_engine()
        profile = _make_profile(budget_ceiling=Decimal("1000000"))

        rfq_fields = {
            "quantity": 100,
            "unit_rate": 500,
        }

        val = engine._compute_valuation(
            profile, is_buyer=False,
            rfq_parsed_fields=rfq_fields,
            catalogue_price=None,
        )

        # Intrinsic = 100 × 500 = ₹50,000 used as cost_basis
        # reservation ≈ 50000 × 1.10 = ₹55,000
        assert val.reservation_price < Decimal("100000"), (
            f"Seller reservation_price {val.reservation_price} should be near ₹55,000 "
            f"(from intrinsic ₹50,000), not from ₹600,000"
        )


# ─── Test 2: Budget ceiling fallback path ────────────────────────────────────


class TestComputeValuationFallbackPath:
    """_compute_valuation falls back to budget_ceiling when RFQ data is missing."""

    def test_fallback_when_rfq_is_none(self) -> None:
        """Budget ceiling used when rfq_parsed_fields is None (freeform session)."""
        engine = _make_engine()
        profile = _make_profile(budget_ceiling=Decimal("1000000"))

        val = engine._compute_valuation(
            profile, is_buyer=True,
            rfq_parsed_fields=None,
            catalogue_price=None,
        )

        # Fallback: fair_price = 1000000 × 0.80 = 800000
        assert val.target_price > Decimal("500000"), (
            f"Fallback buyer target_price {val.target_price} should be derived "
            f"from ₹10L ceiling"
        )

    def test_fallback_when_quantity_missing(self) -> None:
        """Budget ceiling used when parsed_fields lacks 'quantity'."""
        engine = _make_engine()
        profile = _make_profile(budget_ceiling=Decimal("500000"))

        rfq_fields = {
            "unit_rate": 75,
            # "quantity" key missing
        }

        val = engine._compute_valuation(
            profile, is_buyer=True,
            rfq_parsed_fields=rfq_fields,
            catalogue_price=None,
        )

        # Fallback: fair_price = 500000 × 0.80 = 400000
        assert val.target_price > Decimal("200000"), (
            f"Fallback buyer target_price {val.target_price} should be derived "
            f"from ₹5L ceiling (quantity missing in parsed_fields)"
        )

    def test_fallback_when_unit_rate_missing(self) -> None:
        """Budget ceiling used when parsed_fields lacks 'unit_rate'."""
        engine = _make_engine()
        profile = _make_profile(budget_ceiling=Decimal("500000"))

        rfq_fields = {
            "quantity": 600,
            # "unit_rate" key missing
        }

        val = engine._compute_valuation(
            profile, is_buyer=True,
            rfq_parsed_fields=rfq_fields,
            catalogue_price=None,
        )

        # Should fall back to ceiling-based
        assert val.target_price > Decimal("200000"), (
            f"Fallback buyer target_price {val.target_price} should be derived "
            f"from ₹5L ceiling (unit_rate missing)"
        )

    def test_seller_fallback_when_rfq_none(self) -> None:
        """Seller uses budget_ceiling × 0.60 when no RFQ data."""
        engine = _make_engine()
        profile = _make_profile(
            budget_ceiling=Decimal("1000000"),
            margin_floor=Decimal("10"),
        )

        val = engine._compute_valuation(
            profile, is_buyer=False,
            rfq_parsed_fields=None,
            catalogue_price=None,
        )

        # Fallback: cost_basis = 1000000 × 0.60 = 600000
        assert val.reservation_price > Decimal("500000"), (
            f"Fallback seller reservation_price {val.reservation_price} should be "
            f"derived from ₹10L ceiling"
        )


# ─── Test 3: Real-world scenario — 600 Kg @ ₹75/kg ─────────────────────────


class TestRealWorldScenario:
    """
    Regression test for the original bug:
    RFQ for 600 Kg @ ₹75/kg (intrinsic = ₹45,000) should NOT negotiate
    in the ₹7.2L–₹8.5L range.
    """

    def test_600kg_at_75_buyer_fair_price_near_45k(self) -> None:
        """Buyer fair_price derived from ₹45,000 intrinsic, NOT from ₹10L ceiling."""
        engine = _make_engine()
        profile = _make_profile(budget_ceiling=Decimal("1000000"))

        rfq_fields = {
            "quantity": 600,
            "unit_rate": 75,
            "budget_min": 40000,
            "budget_max": 50000,
        }

        val = engine._compute_valuation(
            profile, is_buyer=True,
            rfq_parsed_fields=rfq_fields,
            catalogue_price=Decimal("70"),
        )

        # With budget range midpoint = ₹45,000:
        # Target ≈ 45000 × 0.95 = ₹42,750 (MEDIUM discount 5%)
        # Reservation ≈ min(45000 × 1.10, budget_max=50000) = ₹49,500 or ₹50,000
        assert val.target_price < Decimal("50000"), (
            f"target_price={val.target_price} — must be < ₹50,000 for 600Kg@₹75"
        )
        assert val.target_price > Decimal("30000"), (
            f"target_price={val.target_price} — must be > ₹30,000 (reasonable lower bound)"
        )
        assert val.reservation_price < Decimal("60000"), (
            f"reservation_price={val.reservation_price} — must be < ₹60,000, "
            f"NOT the ₹7.2L from old budget_ceiling logic"
        )

    def test_600kg_at_75_seller_near_intrinsic(self) -> None:
        """Seller valuation based on catalogue ₹70/unit, not ₹600,000 ceiling."""
        engine = _make_engine()
        profile = _make_profile(
            budget_ceiling=Decimal("1000000"),
            margin_floor=Decimal("10"),
        )

        rfq_fields = {
            "quantity": 600,
            "unit_rate": 75,
        }

        val = engine._compute_valuation(
            profile, is_buyer=False,
            rfq_parsed_fields=rfq_fields,
            catalogue_price=Decimal("70"),
        )

        # cost_basis = ₹70 (catalogue), reservation = 70 × 1.10 = ₹77
        # NOT ₹660,000 from old budget_ceiling × 0.60 × 1.10
        assert val.reservation_price < Decimal("200"), (
            f"seller reservation_price={val.reservation_price} — must be < ₹200 "
            f"(from catalogue ₹70), NOT ₹660,000 from ceiling fallback"
        )

    def test_old_bug_would_produce_8_lakh(self) -> None:
        """Confirm that the old ceiling-based logic produces the buggy ₹8L+ values."""
        engine = _make_engine()
        profile = _make_profile(budget_ceiling=Decimal("1000000"))

        # Old path: rfq_parsed_fields=None forces fallback
        val = engine._compute_valuation(
            profile, is_buyer=True,
            rfq_parsed_fields=None,
            catalogue_price=None,
        )

        # Old derivation: fair_price = 10L × 0.80 = 8L, target ≈ 8L × 0.95 = ₹7.6L
        assert val.target_price > Decimal("600000"), (
            f"Ceiling-based target={val.target_price} — confirms old buggy path "
            f"would produce ₹7L+ valuations"
        )


# ─── Test 4: Risk multipliers preserved on intrinsic value ───────────────────


class TestRiskMultipliersPreserved:
    """Risk-profile multipliers are applied on top of intrinsic value."""

    def test_high_risk_buyer_wider_reservation(self) -> None:
        """HIGH risk buyer gets wider reservation zone than MEDIUM."""
        engine = _make_engine()

        rfq_fields = {"quantity": 100, "unit_rate": 500, "budget_min": 40000, "budget_max": 60000}

        medium = engine._compute_valuation(
            _make_profile(risk_appetite="MEDIUM"), is_buyer=True,
            rfq_parsed_fields=rfq_fields, catalogue_price=None,
        )
        high = engine._compute_valuation(
            _make_profile(risk_appetite="HIGH"), is_buyer=True,
            rfq_parsed_fields=rfq_fields, catalogue_price=None,
        )

        # HIGH risk has larger discount target → lower target_price
        assert high.target_price < medium.target_price, (
            f"HIGH risk target={high.target_price} should be < MEDIUM target={medium.target_price}"
        )

    def test_seller_margin_floor_applied(self) -> None:
        """Seller margin_floor is applied on catalogue cost basis."""
        engine = _make_engine()

        rfq_fields = {"quantity": 100, "unit_rate": 500}

        val_10 = engine._compute_valuation(
            _make_profile(margin_floor=Decimal("10")), is_buyer=False,
            rfq_parsed_fields=rfq_fields, catalogue_price=Decimal("400"),
        )
        val_20 = engine._compute_valuation(
            _make_profile(margin_floor=Decimal("20")), is_buyer=False,
            rfq_parsed_fields=rfq_fields, catalogue_price=Decimal("400"),
        )

        # 10% margin: reservation = 400 × 1.10 = 440
        # 20% margin: reservation = 400 × 1.20 = 480
        assert val_20.reservation_price > val_10.reservation_price, (
            f"20% floor reservation={val_20.reservation_price} should be > "
            f"10% floor reservation={val_10.reservation_price}"
        )
