"""Tests fuer KPM-Variante-D Helpers (Rebalance) [CRUX-MK]."""

from decimal import Decimal
import pytest

from src.kpm_variante_d_helpers import (
    TradingContext,
    DrawdownState,
    kelly_fraction_for_context,
    drawdown_cap_check,
    hive_leverage_gate,
    position_reduction_factor,
)


def test_kelly_fraction_matrix():
    assert kelly_fraction_for_context(TradingContext.NORMALREGIME_HIGH_CONFIDENCE) == Decimal("0.40")
    assert kelly_fraction_for_context(TradingContext.HIGH_VOLATILITY) == Decimal("0.25")
    assert kelly_fraction_for_context(TradingContext.REGIME_BREAK) == Decimal("0")


def test_drawdown_cap_thresholds():
    assert drawdown_cap_check(Decimal("14")) == DrawdownState.NORMAL
    assert drawdown_cap_check(Decimal("15")) == DrawdownState.SOFT_BRAKE
    assert drawdown_cap_check(Decimal("20")) == DrawdownState.HARD_CAP
    assert drawdown_cap_check(Decimal("25")) == DrawdownState.ABSOLUTE_NO_GO


def test_hive_leverage_gate_decisions():
    assert hive_leverage_gate(Decimal("0.4")) == "auto_deleverage"
    assert hive_leverage_gate(Decimal("0.6")) == "no_leverage_increase"
    assert hive_leverage_gate(Decimal("0.7")) == "leverage_ok"


def test_position_reduction_factor():
    assert position_reduction_factor(DrawdownState.NORMAL) == Decimal("1.0")
    assert position_reduction_factor(DrawdownState.SOFT_BRAKE) == Decimal("0.5")
    assert position_reduction_factor(DrawdownState.HARD_CAP) == Decimal("0.0")
