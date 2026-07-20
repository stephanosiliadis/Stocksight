"""Hand-verifiable checks for Phase 3 Day 2 (risk/reward + position sizing)."""
from __future__ import annotations

import math

from src.services.position_sizing_service import PositionSizingService
from src.services.risk_service import RiskService


def _example1():
    # $10,000 account, 1% risk, $100 entry, $95 stop.
    # risk_amount = 100, risk_distance = 5, shares = floor(100/5) = 20.
    ps = PositionSizingService().serve_position_size(10000, 0.01, 100, 95)
    assert ps.shares == 20
    assert math.isclose(ps.dollar_amount, 2000.0)
    assert math.isclose(ps.risk_amount, 100.0)
    assert math.isclose(ps.risk_pct, 0.01)


def _example2():
    # $25,000 account, 0.5% risk, $52.40 entry, $50.00 stop.
    # risk_amount = 125, risk_distance = 2.40, shares = floor(125/2.40) = 52.
    ps = PositionSizingService().serve_position_size(25000, 0.005, 52.40, 50.00)
    assert ps.shares == 52
    assert math.isclose(ps.dollar_amount, 52 * 52.40)
    assert math.isclose(ps.dollar_amount, 2724.80)
    assert math.isclose(ps.risk_amount, 125.0)
    assert math.isclose(ps.risk_pct, 0.005)


def _example3():
    # $5,000 account, 2% risk, $17.25 entry, $18.05 stop.
    # risk_amount = 100, risk_distance = 0.80, shares = floor(100/0.80) = 125.
    ps = PositionSizingService().serve_position_size(5000, 0.02, 17.25, 18.05)
    assert ps.shares == 125
    assert math.isclose(ps.dollar_amount, 125 * 17.25)
    assert math.isclose(ps.dollar_amount, 2156.25)
    assert math.isclose(ps.risk_amount, 100.0)


def test_risk_reward_long():
    rr = RiskService.calculate_risk_reward(100, 95, 110)
    assert math.isclose(rr, 2.0)


def test_risk_reward_invalid_returns_zero():
    # Stop at or above entry, or target at or below entry -> not a valid long.
    assert RiskService.calculate_risk_reward(100, 100, 110) == 0.0
    assert RiskService.calculate_risk_reward(100, 95, 90) == 0.0
    assert RiskService.calculate_risk_reward(100, 110, 120) == 0.0


def test_position_size_invalid_inputs_yield_zero_shares():
    # Stop at entry => zero risk distance => no trade.
    ps = PositionSizingService().serve_position_size(10000, 0.01, 100, 100)
    assert ps.shares == 0
    assert ps.dollar_amount == 0.0
    # Bad account size => no trade.
    ps2 = PositionSizingService().serve_position_size(0, 0.01, 100, 95)
    assert ps2.shares == 0
    # Negative entry => no trade.
    ps3 = PositionSizingService().serve_position_size(10000, 0.01, -1, 95)
    assert ps3.shares == 0


def test_all_examples():
    _example1()
    _example2()
    _example3()
