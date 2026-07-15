from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import adapter_orchestrator


def _run_engine(tmp_path: Path, payload: dict[str, object], name: str) -> dict[str, object]:
    input_path = tmp_path / f"{name}-risk.json"
    output_path = tmp_path / f"{name}-recommendation.json"
    audit_path = tmp_path / "audit.jsonl"
    input_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(Path(adapter_orchestrator.__file__).resolve()),
            "--input",
            str(input_path),
            "--output",
            str(output_path),
            "--audit-log",
            str(audit_path),
        ],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert output_path.exists()
    assert audit_path.exists()

    recommendation = json.loads(output_path.read_text(encoding="utf-8"))
    audit_events = [
        json.loads(line)
        for line in audit_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert audit_events[-1]["recommendation_id"] == recommendation["recommendation_id"]
    assert audit_events[-1]["input_hash"] == recommendation["input_hash"]
    return recommendation


def test_rebalance_engine_discriminates_adversarial_drawdown_from_calm_input(tmp_path: Path):
    calm_snapshot = {
        "current_drawdown_pct": "4.8",
        "trading_context": "normal_avg",
        "max_drift_pct": "2.5",
        "source": "file",
    }
    adversarial_snapshot = {
        "current_drawdown_pct": "27.2",
        "trading_context": "regime_break",
        "max_drift_pct": "18.0",
        "source": "file",
    }

    calm = _run_engine(tmp_path, calm_snapshot, "calm")
    adversarial = _run_engine(tmp_path, adversarial_snapshot, "adversarial")

    assert calm["input_hash"] != adversarial["input_hash"]
    assert calm["recommendation_id"] != adversarial["recommendation_id"]
    assert calm["action"] != adversarial["action"]
    assert calm["drawdown_state"] != adversarial["drawdown_state"]
    assert calm["position_multiplier"] != adversarial["position_multiplier"]
    assert calm["suggested_kelly_fraction"] != adversarial["suggested_kelly_fraction"]

    assert calm["action"] == "none"
    assert calm["drawdown_state"] == "normal"
    assert calm["position_multiplier"] == "1.0"
    assert adversarial["action"] == "emergency_halt"
    assert adversarial["drawdown_state"] == "absolute_no_go"
    assert adversarial["position_multiplier"] == "0.0"
