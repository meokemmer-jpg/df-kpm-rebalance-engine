# df-kpm-rebalance-engine — Output [CRUX-MK]
*Autonom aktiviert 2026-06-05T11:03:35.713152+00:00 | ollama-local/qwen2.5:14b-instruct*

# DF-KPM-Rebalance-Engine [CRUX-MK]

## Bayesian-Yield-Manager für KPM-Rebalance-Decisions

### Kelly-Fraction-Calculator pro Trading-Kontext
Die `src/rebalance_engine_main.py` implementiert eine bayesianische Entsche
Entscheidungslogik, die auf der Kelly-Formel basiert, um optimale Wetten in
in jedem Handelskontext zu berechnen. Diese Logik berücksichtigt den aktuel
aktuellen Portfolio-Wert und den gegebenen Risikofaktor.

### Anti-Drawdown-Soft-Brake
Eine grundlegende Bestandteil des Systems ist der Anti-Drawdown-Mechanismus
Anti-Drawdown-Mechanismus, der eine sanfte Bremse bei einem Drawdown von 15
15% auslöst. Dies wird durch die Datei `src/kpm_variante_d_helpers.py` verw
verwaltet und sorgt dafür, dass das System risikomindernd reagiert, wenn ei
ein bestimmter Verlustniveau erreicht wurde.

### Konsens-Check mit Variante-D-Limits
Der Check des Systems läuft auf der Überprüfung der Entscheidungen anhand v
von Variante-D-Grenzwerten. Diese Prüfungen stellen sicher, dass alle Empfe
Empfehlungen den strengen Compliance-Anforderungen entsprechen und innerhal
innerhalb der vorgesehenen Grenzen operieren.

### Sandbox-Default ohne Real-Trade-Execution
Die DF-KPM-Rebalance-Engine operiert standardmäßig in einem sandbox-Umgebun
sandbox-Umgebung. Hier wird nur eine Empfehlung an KPM generiert, aber kein
keine tatsächlichen Handelsaktionen durchgeführt. Das Umstellen auf reale T
Transaktionen ist möglich, jedoch unter strengen Sicherheitsrichtlinien:

```bash
DF_KPM_REBALANCE_REAL_ENABLED=false # Standard
```

### Architektur

- **`src/rebalance_engine_main.py`**: Implementiert die bayesianische Entsc
Entscheidungslogik und den Kelly-Fraktionsrechner.
- **`src/kpm_variante_d_helpers.py`**: Enthält Funktionen zur Berechnung de
der Kelly-Fraktion sowie zur Handhabung von Anti-Drawdown-Mechanismen.
- **`src/adapter_orchestrator.py`**: Dies ist die Einstiegspunkt für Launch
LaunchAgent und organisiert den Ablauf aller notwendigen Prozesse.
- **`src/audit_logger.py`**: Verwendet HMAC-SHA256 zur Generierung eines Au
Audits, um alle Aktivitäten des Systems zu dokumentieren.

### CRUX-Bindung

- **K_0:** Die DF empfiehlt nur Rebalance-Aktionen und führt keine echten H
Handlungen aus.
- **Q_0:** Sorgt für konsistente Compliance-Empfehlungen gemäß Variante-D-A
Variante-D-Anforderungen.
- **W_0:** Minimiert die Martin-Bandbreite durch Bereitstellung präkompilie
präkompilierte Empfehlungen, um die Effizienz der KPM zu steigern.

---

Diese DF-KPM-Rebalance-Engine ist eine wesentliche Komponente in unserem Po
Portfolio-Managementsystem und trägt erheblich zum Erreichen unserer strate
strategischen Ziele bei.