"""DF-KPM-Rebalance-Engine Core-Logic [CRUX-MK].

Bayesian-Yield-Manager fuer Rebalance-Empfehlungen.
KEINE Trade-Execution. Nur Recommendations.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional

from .kpm_variante_d_helpers import (
    TradingContext,
    DrawdownState,
    kelly_fraction_for_context,
    drawdown_cap_check,
    position_reduction_factor,
)


class RebalanceAction(Enum):
    """Empfohlene Rebalance-Aktion."""
    NONE = "none"  # Innerhalb Tolerance
    REDUCE_POSITION = "reduce_position"  # Soft-Brake
    PAUSE_TRADING = "pause_trading"  # Hard-Cap + Phronesis
    EMERGENCY_HALT = "emergency_halt"  # Absolute-No-Go
    REBALANCE_TO_TARGET = "rebalance_to_target"  # Drift > 10pp


@dataclass(frozen=True)
class RebalanceRecommendation:
    """Output des Bayesian-Yield-Managers."""
    recommendation_id: str
    timestamp: str
    action: RebalanceAction
    suggested_kelly_fraction: Decimal
    drawdown_state: DrawdownState
    position_multiplier: Decimal  # 0.0 - 1.0
    reasoning: str
    source: str  # "mock" | "real-api"
    phronesis_ticket: Optional[str] = None

    def __post_init__(self):
        if self.source == "real-api" and not self.phronesis_ticket:
            raise ValueError("Real-API recommendations require phronesis_ticket")
        if self.position_multiplier < Decimal("0") or self.position_multiplier > Decimal("1"):
            raise ValueError(f"position_multiplier must be 0-1, got {self.position_multiplier}")


class BayesianYieldEstimator:
    """Bayesian-Posterior-Update fuer erwartete Yields.

    Vereinfachte Variante-D-Implementation (Phase-1 Mock).
    Real-Bayesian-Inference in Phase-2 (PyMC/numpyro).
    """

    @staticmethod
    def estimate_expected_yield(
        prior_mean: Decimal,
        prior_std: Decimal,
        observation: Decimal,
        observation_std: Decimal,
    ) -> tuple[Decimal, Decimal]:
        """Conjugate-Normal Bayesian-Update (Mock-Phase-1).

        Returns:
            (posterior_mean, posterior_std)
        """
        # Vereinfachte Conjugate-Normal-Update
        prior_var = prior_std ** 2
        obs_var = observation_std ** 2
        if prior_var + obs_var == Decimal("0"):
            return prior_mean, prior_std
        weight_prior = obs_var / (prior_var + obs_var)
        weight_obs = prior_var / (prior_var + obs_var)
        posterior_mean = weight_prior * prior_mean + weight_obs * observation
        posterior_var = (prior_var * obs_var) / (prior_var + obs_var)
        # Decimal sqrt approximation
        posterior_std = Decimal(str(float(posterior_var) ** 0.5))
        return posterior_mean, posterior_std


def compute_rebalance_recommendation(
    current_drawdown_pct: Decimal,
    trading_context: TradingContext,
    max_drift_pct: Decimal,
    source: str = "mock",
    phronesis_ticket: Optional[str] = None,
) -> RebalanceRecommendation:
    """Computes Rebalance-Recommendation per Variante-D-Logic.

    Args:
        current_drawdown_pct: Akkumulierter Drawdown
        trading_context: Aktueller Markt-Kontext
        max_drift_pct: Max Allocation-Drift in Portfolio
        source: 'mock' | 'real-api'
        phronesis_ticket: Pflicht bei real-api
    """
    drawdown_state = drawdown_cap_check(current_drawdown_pct)
    kelly = kelly_fraction_for_context(trading_context)
    position_mult = position_reduction_factor(drawdown_state)

    # Action-Decision Tree
    if drawdown_state == DrawdownState.ABSOLUTE_NO_GO:
        action = RebalanceAction.EMERGENCY_HALT
        reasoning = f"Drawdown {current_drawdown_pct}% >= 25% (Familien-Notfall-Protokoll)"
    elif drawdown_state == DrawdownState.HARD_CAP:
        action = RebalanceAction.PAUSE_TRADING
        reasoning = f"Drawdown {current_drawdown_pct}% >= 20% (Trading-Pause + Phronesis-Pflicht)"
    elif drawdown_state == DrawdownState.SOFT_BRAKE:
        action = RebalanceAction.REDUCE_POSITION
        reasoning = f"Drawdown {current_drawdown_pct}% >= 15% (Position-Reduktion 50%)"
    elif max_drift_pct >= Decimal("10"):
        action = RebalanceAction.REBALANCE_TO_TARGET
        reasoning = f"Drift {max_drift_pct}pp >= 10pp (Rebalance-Trigger)"
    else:
        action = RebalanceAction.NONE
        reasoning = f"Drawdown {current_drawdown_pct}% normal, drift {max_drift_pct}pp tolerable"

    return RebalanceRecommendation(
        recommendation_id=f"rec-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}",
        timestamp=datetime.now(timezone.utc).isoformat(),
        action=action,
        suggested_kelly_fraction=kelly,
        drawdown_state=drawdown_state,
        position_multiplier=position_mult,
        reasoning=reasoning,
        source=source,
        phronesis_ticket=phronesis_ticket,
    )


def get_default_mode() -> str:
    """Returns 'mock' (default) or 'real-api'."""
    if os.environ.get("DF_KPM_REBALANCE_REAL_ENABLED") == "true":
        return "real-api"
    return "mock"
