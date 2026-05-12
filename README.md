# DF-KPM-Rebalance-Engine [CRUX-MK]

**Welle-42 Foundation-DF für KPM (Kemmer-Portfolio-Management)**
**Per `~/.claude/rules/kpm-sizing.md` Variante-D-Hybrid**

## Zweck

Bayesian-Yield-Manager für KPM-Rebalance-Decisions:
- Kelly-Fraction-Calculator pro Trading-Kontext
- Anti-Drawdown-Soft-Brake bei 15%
- Konsens-Check mit Variante-D-Limits
- Sandbox-Default ohne Real-Trade-Execution

## K_0-MAX-Berührung

KEINE Real-Trade-Execution. Diese DF empfiehlt nur Rebalance-Actions.
- Sandbox-Default mit Mock-Empfehlungen
- Phronesis-Pflicht Martin pro Real-Mode-Aktivieren
- ENV-Var `DF_KPM_REBALANCE_REAL_ENABLED=false` (default)

## Architektur

- `src/rebalance_engine_main.py` - Bayesian-Decision-Logic
- `src/kpm_variante_d_helpers.py` - Kelly + Drawdown
- `src/adapter_orchestrator.py` - LaunchAgent-Entry
- `src/audit_logger.py` - HMAC-SHA256 Audit

## CRUX-Bindung

- **K_0:** Empfehlungs-only, keine Auto-Trades
- **Q_0:** Konsistente Variante-D-Compliance-Empfehlungen
- **W_0:** Martin-Bandbreite minimiert via Pre-Computed-Recommendations

[CRUX-MK]
