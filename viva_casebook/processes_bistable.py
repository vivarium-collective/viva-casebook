"""A genetic toggle switch (mutual repression) as a real process-bigraph Process.

Two genes A and B each repress the other:

    dA/dt = beta / (1 + (B/K)^n)  -  deg * A
    dB/dt = beta / (1 + (A/K)^n)  -  deg * B

The behaviour hinges on the Hill exponent n (cooperativity of repression):

  - n = 1 (non-cooperative): a single, symmetric stable state — MONOSTABLE.
    Every initial condition relaxes to A == B. No switch.
  - n >= 2 (cooperative/ultrasensitive): the symmetric state loses stability and
    two asymmetric stable states appear — BISTABLE. The system latches to whichever
    gene starts ahead (A-high or B-high).

Bistability is a STRUCTURAL property that only cooperative feedback creates; no
amount of tuning a single expression/degradation knob produces two basins from a
non-cooperative switch. That is what makes this a genuine agent task.
"""
from __future__ import annotations

from process_bigraph import Process


def _f(default):
    return {"_type": "float", "_default": default}


class ToggleSwitch(Process):
    config_schema = {"beta": _f(4.0), "K": _f(1.0), "n": _f(1.0), "deg": _f(1.0)}

    def inputs(self):
        return {"A": "float", "B": "float"}

    def outputs(self):
        return {"A": "float", "B": "float"}

    def update(self, state, interval):
        A = max(0.0, float(state.get("A", 0.0)))
        B = max(0.0, float(state.get("B", 0.0)))
        c = self.config
        beta, K, n, deg = c["beta"], c["K"], c["n"], c["deg"]
        dA = (beta / (1.0 + (B / K) ** n) - deg * A) * interval
        dB = (beta / (1.0 + (A / K) ** n) - deg * B) * interval
        return {"A": max(dA, -A), "B": max(dB, -B)}
