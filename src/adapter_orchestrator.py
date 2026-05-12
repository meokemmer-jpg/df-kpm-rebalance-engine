"""DF-KPM-Rebalance-Engine LaunchAgent-Entry [CRUX-MK]."""

from __future__ import annotations

import json
import os
import sys
from decimal import Decimal
from pathlib import Path

from .rebalance_engine_main import (
    compute_rebalance_recommendation,
    get_default_mode,
)
from .kpm_variante_d_helpers import TradingContext
from .audit_logger import log_audit_event


def main(argv: list[str] | None = None) -> int:
    """LaunchAgent-Entry-Point. Returns: 0=ok, 1=err, 2=stop, 3=k16-veto."""
    stop_flag = Path("/tmp/df-kpm-rebalance-engine.stop")
    if stop_flag.exists():
        print(f"STOP.flag detected at {stop_flag}", file=sys.stderr)
        return 2

    mode = get_default_mode()
    if mode == "real-api" and not os.environ.get("PHRONESIS_TICKET"):
        print("Real-API-Mode requires PHRONESIS_TICKET", file=sys.stderr)
        log_audit_event(
            event="real_mode_rejected_no_phronesis",
            df_id="df-kpm-rebalance-engine",
            details={"reason": "PHRONESIS_TICKET missing"},
        )
        return 1

    # Phase-1 Mock-Default: simuliere Normalregime + low drawdown
    rec = compute_rebalance_recommendation(
        current_drawdown_pct=Decimal("8"),  # mock 8% drawdown
        trading_context=TradingContext.NORMALREGIME_AVG_CONFIDENCE,
        max_drift_pct=Decimal("3"),
        source="mock",
    )

    log_audit_event(
        event="recommendation_computed",
        df_id="df-kpm-rebalance-engine",
        details={
            "recommendation_id": rec.recommendation_id,
            "action": rec.action.value,
            "kelly_fraction": str(rec.suggested_kelly_fraction),
            "drawdown_state": rec.drawdown_state.value,
            "source": rec.source,
        },
    )

    health_data = {
        "status": "ok",
        "timestamp": rec.timestamp,
        "last_action": rec.action.value,
        "source": rec.source,
    }
    health_path = Path("/tmp/df-kpm-rebalance-engine-health.json")
    try:
        health_path.write_text(json.dumps(health_data, indent=2))
    except Exception as e:
        print(f"Could not write health: {e}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
