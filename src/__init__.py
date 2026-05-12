"""DF-KPM-Rebalance-Engine package [CRUX-MK]. Lazy-Import-Pattern."""

__version__ = "0.1.0-PHASE-1"


def __getattr__(name):
    if name == "RebalanceRecommendation":
        from .rebalance_engine_main import RebalanceRecommendation
        return RebalanceRecommendation
    if name == "BayesianYieldEstimator":
        from .rebalance_engine_main import BayesianYieldEstimator
        return BayesianYieldEstimator
    if name == "compute_rebalance_recommendation":
        from .rebalance_engine_main import compute_rebalance_recommendation
        return compute_rebalance_recommendation
    if name == "kelly_fraction_for_context":
        from .kpm_variante_d_helpers import kelly_fraction_for_context
        return kelly_fraction_for_context
    raise AttributeError(f"module {__name__} has no attribute {name}")
