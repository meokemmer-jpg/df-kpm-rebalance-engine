
# K12+K13+K16 Trinity-CONTRARIAN 2026-05-17 (Cross-LLM-validated)
def k12_provenance(payload: bytes, key: bytes = b"df-trinity-contrarian-v1") -> dict:
    import hashlib, hmac
    return {
        "payload_hash": hashlib.sha256(payload).hexdigest(),
        "hmac_sha256": hmac.new(key, payload, hashlib.sha256).hexdigest(),
    }

def k13_anchor(payload_hash: str) -> dict:
    from datetime import datetime, timezone
    return {
        "anchor_type": "rfc3161-mock",
        "iso_ts": datetime.now(timezone.utc).isoformat(),
        "payload_hash": payload_hash,
    }

def k16_lock_or_exit(df_name: str):
    import fcntl, os, sys
    lock_path = f"/tmp/df-trinity-{df_name}.lock"
    fd = os.open(lock_path, os.O_CREAT | os.O_WRONLY)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return fd
    except BlockingIOError:
        sys.exit(3)

"""Tests fuer DF-KPM-Rebalance-Engine Core-Logic [CRUX-MK]."""

from __future__ import annotations

from decimal import Decimal

import pytest

from src.rebalance_engine_main import (
    RebalanceAction,
    RebalanceRecommendation,
    BayesianYieldEstimator,
    compute_rebalance_recommendation,
    get_default_mode,
)
from src.kpm_variante_d_helpers import TradingContext, DrawdownState


def test_rebalance_recommendation_real_api_requires_phronesis():
    """Real-API-Recommendations brauchen phronesis_ticket."""
    with pytest.raises(ValueError, match="phronesis_ticket"):
        RebalanceRecommendation(
            recommendation_id="test",
            timestamp="2026-05-11T10:00:00+00:00",
            action=RebalanceAction.NONE,
            suggested_kelly_fraction=Decimal("0.30"),
            drawdown_state=DrawdownState.NORMAL,
            position_multiplier=Decimal("1.0"),
            reasoning="test",
            source="real-api",
            phronesis_ticket=None,
        )


def test_rebalance_recommendation_position_multiplier_validated():
    """position_multiplier muss 0-1 sein."""
    with pytest.raises(ValueError, match="position_multiplier"):
        RebalanceRecommendation(
            recommendation_id="test",
            timestamp="2026-05-11T10:00:00+00:00",
            action=RebalanceAction.NONE,
            suggested_kelly_fraction=Decimal("0.30"),
            drawdown_state=DrawdownState.NORMAL,
            position_multiplier=Decimal("1.5"),
            reasoning="test",
            source="mock",
        )


def test_compute_recommendation_normal_state():
    """Normalregime + low drawdown + low drift = NONE."""
    rec = compute_rebalance_recommendation(
        current_drawdown_pct=Decimal("5"),
        trading_context=TradingContext.NORMALREGIME_AVG_CONFIDENCE,
        max_drift_pct=Decimal("3"),
    )
    assert rec.action == RebalanceAction.NONE
    assert rec.drawdown_state == DrawdownState.NORMAL
    assert rec.position_multiplier == Decimal("1.0")


def test_compute_recommendation_soft_brake():
    """15-20% drawdown -> REDUCE_POSITION."""
    rec = compute_rebalance_recommendation(
        current_drawdown_pct=Decimal("17"),
        trading_context=TradingContext.NORMALREGIME_AVG_CONFIDENCE,
        max_drift_pct=Decimal("3"),
    )
    assert rec.action == RebalanceAction.REDUCE_POSITION
    assert rec.drawdown_state == DrawdownState.SOFT_BRAKE
    assert rec.position_multiplier == Decimal("0.5")


def test_compute_recommendation_hard_cap():
    """20-25% drawdown -> PAUSE_TRADING (Phronesis)."""
    rec = compute_rebalance_recommendation(
        current_drawdown_pct=Decimal("22"),
        trading_context=TradingContext.HIGH_VOLATILITY,
        max_drift_pct=Decimal("3"),
    )
    assert rec.action == RebalanceAction.PAUSE_TRADING
    assert rec.drawdown_state == DrawdownState.HARD_CAP


def test_compute_recommendation_emergency():
    """>= 25% drawdown -> EMERGENCY_HALT."""
    rec = compute_rebalance_recommendation(
        current_drawdown_pct=Decimal("28"),
        trading_context=TradingContext.HIGH_VOLATILITY,
        max_drift_pct=Decimal("3"),
    )
    assert rec.action == RebalanceAction.EMERGENCY_HALT
    assert rec.drawdown_state == DrawdownState.ABSOLUTE_NO_GO


def test_compute_recommendation_drift_trigger():
    """Drift >= 10pp triggert REBALANCE_TO_TARGET."""
    rec = compute_rebalance_recommendation(
        current_drawdown_pct=Decimal("5"),
        trading_context=TradingContext.NORMALREGIME_AVG_CONFIDENCE,
        max_drift_pct=Decimal("12"),
    )
    assert rec.action == RebalanceAction.REBALANCE_TO_TARGET


def test_bayesian_update_conjugate_normal():
    """Bayesian-Update reduziert Posterior-Std."""
    posterior_mean, posterior_std = BayesianYieldEstimator.estimate_expected_yield(
        prior_mean=Decimal("0.07"),
        prior_std=Decimal("0.03"),
        observation=Decimal("0.10"),
        observation_std=Decimal("0.02"),
    )
    # Posterior between prior and observation
    assert Decimal("0.07") < posterior_mean < Decimal("0.10")
    # Posterior std smaller than both
    assert posterior_std < Decimal("0.03")
    assert posterior_std < Decimal("0.02")


def test_get_default_mode_sandbox(monkeypatch):
    """Default ist mock."""
    monkeypatch.delenv("DF_KPM_REBALANCE_REAL_ENABLED", raising=False)
    assert get_default_mode() == "mock"


def test_get_default_mode_real_strict(monkeypatch):
    """Nur 'true' aktiviert Real-Mode."""
    monkeypatch.setenv("DF_KPM_REBALANCE_REAL_ENABLED", "yes")
    assert get_default_mode() == "mock"
    monkeypatch.setenv("DF_KPM_REBALANCE_REAL_ENABLED", "true")
    assert get_default_mode() == "real-api"
