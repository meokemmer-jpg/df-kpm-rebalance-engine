"""File-backed DF-KPM rebalance engine entrypoint.

The adapter reads a portfolio risk snapshot from JSON, computes a deterministic
rebalance recommendation from the supplied values, writes the recommendation to
JSON, and appends an audit record. It does not execute trades.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from enum import Enum
from pathlib import Path
from typing import Any


DF_ID = "df-kpm-rebalance-engine"


class RebalanceAction(Enum):
    """Supported rebalance recommendations."""

    NONE = "none"
    REDUCE_POSITION = "reduce_position"
    PAUSE_TRADING = "pause_trading"
    EMERGENCY_HALT = "emergency_halt"
    REBALANCE_TO_TARGET = "rebalance_to_target"


class DrawdownState(Enum):
    """Drawdown regime derived from current drawdown percentage."""

    NORMAL = "normal"
    SOFT_BRAKE = "soft_brake"
    HARD_CAP = "hard_cap"
    ABSOLUTE_NO_GO = "absolute_no_go"


class TradingContext(Enum):
    """Market and portfolio context used for Kelly sizing."""

    NORMALREGIME_HIGH_CONFIDENCE = "normal_high"
    NORMALREGIME_AVG_CONFIDENCE = "normal_avg"
    HIGH_VOLATILITY = "high_vol"
    WITHDRAWAL_PHASE = "withdrawal"
    REGIME_BREAK = "regime_break"


KELLY_FRACTION_BY_CONTEXT: dict[TradingContext, Decimal] = {
    TradingContext.NORMALREGIME_HIGH_CONFIDENCE: Decimal("0.40"),
    TradingContext.NORMALREGIME_AVG_CONFIDENCE: Decimal("0.30"),
    TradingContext.HIGH_VOLATILITY: Decimal("0.25"),
    TradingContext.WITHDRAWAL_PHASE: Decimal("0.20"),
    TradingContext.REGIME_BREAK: Decimal("0.00"),
}


@dataclass(frozen=True)
class RiskSnapshot:
    """Input state consumed by the rebalance engine."""

    current_drawdown_pct: Decimal
    trading_context: TradingContext
    max_drift_pct: Decimal
    source: str = "file"
    phronesis_ticket: str | None = None


@dataclass(frozen=True)
class RebalanceRecommendation:
    """Computed rebalance recommendation."""

    recommendation_id: str
    timestamp: str
    action: RebalanceAction
    suggested_kelly_fraction: Decimal
    drawdown_state: DrawdownState
    position_multiplier: Decimal
    reasoning: str
    source: str
    input_hash: str
    phronesis_ticket: str | None = None


def _decimal_from_payload(payload: dict[str, Any], key: str) -> Decimal:
    if key not in payload:
        raise ValueError(f"Missing required field: {key}")
    try:
        value = Decimal(str(payload[key]))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{key} must be decimal-compatible") from exc
    if value.is_nan():
        raise ValueError(f"{key} must not be NaN")
    return value


def _snapshot_from_payload(payload: dict[str, Any]) -> RiskSnapshot:
    context_value = payload.get("trading_context")
    try:
        trading_context = TradingContext(str(context_value))
    except ValueError as exc:
        allowed = ", ".join(context.value for context in TradingContext)
        raise ValueError(f"trading_context must be one of: {allowed}") from exc

    snapshot = RiskSnapshot(
        current_drawdown_pct=_decimal_from_payload(payload, "current_drawdown_pct"),
        trading_context=trading_context,
        max_drift_pct=_decimal_from_payload(payload, "max_drift_pct"),
        source=str(payload.get("source", "file")),
        phronesis_ticket=payload.get("phronesis_ticket"),
    )
    if snapshot.current_drawdown_pct < Decimal("0"):
        raise ValueError("current_drawdown_pct must be >= 0")
    if snapshot.max_drift_pct < Decimal("0"):
        raise ValueError("max_drift_pct must be >= 0")
    if snapshot.source == "real-api" and not snapshot.phronesis_ticket:
        raise ValueError("real-api source requires phronesis_ticket")
    return snapshot


def load_risk_snapshot(path: Path) -> tuple[RiskSnapshot, str]:
    """Read and validate a risk snapshot from disk."""

    raw = path.read_bytes()
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Input JSON must be an object")
    return _snapshot_from_payload(payload), hashlib.sha256(raw).hexdigest()


def classify_drawdown(drawdown_pct: Decimal) -> DrawdownState:
    """Classify drawdown using KPM guardrail thresholds."""

    if drawdown_pct >= Decimal("25"):
        return DrawdownState.ABSOLUTE_NO_GO
    if drawdown_pct >= Decimal("20"):
        return DrawdownState.HARD_CAP
    if drawdown_pct >= Decimal("15"):
        return DrawdownState.SOFT_BRAKE
    return DrawdownState.NORMAL


def position_multiplier_for(drawdown_state: DrawdownState) -> Decimal:
    """Translate drawdown state into maximum position exposure."""

    if drawdown_state == DrawdownState.NORMAL:
        return Decimal("1.0")
    if drawdown_state == DrawdownState.SOFT_BRAKE:
        return Decimal("0.5")
    return Decimal("0.0")


def compute_rebalance_recommendation(
    snapshot: RiskSnapshot,
    *,
    input_hash: str,
    now: datetime | None = None,
) -> RebalanceRecommendation:
    """Compute the recommendation from the supplied snapshot."""

    timestamp_dt = now or datetime.now(timezone.utc)
    drawdown_state = classify_drawdown(snapshot.current_drawdown_pct)
    position_multiplier = position_multiplier_for(drawdown_state)
    kelly_fraction = KELLY_FRACTION_BY_CONTEXT[snapshot.trading_context]

    if drawdown_state == DrawdownState.ABSOLUTE_NO_GO:
        action = RebalanceAction.EMERGENCY_HALT
        reasoning = f"drawdown {snapshot.current_drawdown_pct}% reached absolute no-go"
    elif drawdown_state == DrawdownState.HARD_CAP:
        action = RebalanceAction.PAUSE_TRADING
        reasoning = f"drawdown {snapshot.current_drawdown_pct}% reached hard cap"
    elif drawdown_state == DrawdownState.SOFT_BRAKE:
        action = RebalanceAction.REDUCE_POSITION
        reasoning = f"drawdown {snapshot.current_drawdown_pct}% reached soft brake"
    elif snapshot.max_drift_pct >= Decimal("10"):
        action = RebalanceAction.REBALANCE_TO_TARGET
        reasoning = f"allocation drift {snapshot.max_drift_pct}pp reached rebalance trigger"
    else:
        action = RebalanceAction.NONE
        reasoning = "drawdown and allocation drift are inside guardrails"

    return RebalanceRecommendation(
        recommendation_id=f"rec-{input_hash[:12]}",
        timestamp=timestamp_dt.isoformat(),
        action=action,
        suggested_kelly_fraction=kelly_fraction,
        drawdown_state=drawdown_state,
        position_multiplier=position_multiplier,
        reasoning=reasoning,
        source=snapshot.source,
        input_hash=input_hash,
        phronesis_ticket=snapshot.phronesis_ticket,
    )


def _json_ready(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {key: _json_ready(inner) for key, inner in value.items()}
    return value


def write_recommendation(path: Path, recommendation: RebalanceRecommendation) -> None:
    """Persist the recommendation JSON atomically enough for local agent use."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(_json_ready(asdict(recommendation)), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def append_audit_event(path: Path, recommendation: RebalanceRecommendation) -> None:
    """Append a machine-readable audit event to disk."""

    path.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "event": "recommendation_computed",
        "df_id": DF_ID,
        "timestamp": recommendation.timestamp,
        "recommendation_id": recommendation.recommendation_id,
        "action": recommendation.action.value,
        "drawdown_state": recommendation.drawdown_state.value,
        "input_hash": recommendation.input_hash,
        "source": recommendation.source,
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compute a DF-KPM rebalance recommendation.")
    parser.add_argument("--input", required=True, type=Path, help="Path to risk snapshot JSON.")
    parser.add_argument("--output", required=True, type=Path, help="Path for recommendation JSON.")
    parser.add_argument(
        "--audit-log",
        type=Path,
        default=Path("/tmp/df-kpm-rebalance-engine-audit.jsonl"),
        help="Path for audit JSONL.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint. Returns 0 on success and 1 on validation/runtime errors."""

    stop_flag = Path(os.environ.get("DF_KPM_REBALANCE_STOP_FLAG", "/tmp/df-kpm-rebalance-engine.stop"))
    if stop_flag.exists():
        print(f"STOP.flag detected at {stop_flag}", file=sys.stderr)
        return 2

    args = build_parser().parse_args(argv)
    try:
        snapshot, input_hash = load_risk_snapshot(args.input)
        recommendation = compute_rebalance_recommendation(snapshot, input_hash=input_hash)
        write_recommendation(args.output, recommendation)
        append_audit_event(args.audit_log, recommendation)
    except Exception as exc:
        print(f"{DF_ID}: {exc}", file=sys.stderr)
        return 1
    return 0


def __df_guarded_entry() -> int:
    return main(sys.argv[1:])


def __df_guarded_entry():  # K16+K11-FOUNDATION-WIRED [CRUX-MK]
    raise SystemExit(__df_guarded_entry())

if __name__ == "__main__":  # K16+K11-FOUNDATION-WIRED [CRUX-MK]
    try:
        from _df_common.df_foundation import run_guarded as _rg
    except Exception:
        raise SystemExit(__df_guarded_entry())   # Foundation weg -> normal
    raise SystemExit(_rg("df-kpm-rebalance-engine", __df_guarded_entry))   # K14+K16+K15+K11 echt
