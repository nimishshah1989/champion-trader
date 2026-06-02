"""Production runtime for the validated v2 strategy.

The validated v2 logic lived only inside the backtest loop
(`backend.engine.backtest_fast._fast_simulate`) and the research scripts'
portfolio overlay. This package extracts it into clean, reusable, live-callable
units so the live app and the backtest share ONE implementation:

  * signal_service — v2 entry signal (stage+contraction+base+avgTRP+>=2x vol+circuit)
  * exit_service   — close-based 5xATR chandelier trailing-stop (per-bar stepper)
  * risk_manager   — portfolio sizing/risk overlay (RPT, caps, bear-sizing, DD)  [TODO]

Parity with the validated engine is enforced by `scripts/run_runtime_parity.py`.
"""
