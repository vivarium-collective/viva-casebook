"""Ambiguous-diagnosis mechanisms as real process-bigraph Processes.

"Biomass is too low" — but WHY? Growth here is gated by viability, so a cell that
is dying (viability crashing) grows little even when uptake and yield are fine.
The low-growth margin alone can't tell you the cause; you must read the JOINT
observables (nutrient consumed? viability crashed?) to diagnose it. The correct
fix depends on the diagnosis, which a margin-hill-climber cannot make.
"""
from __future__ import annotations

from process_bigraph import Process


def _f(default):
    return {"_type": "float", "_default": default}


class CellGrowth(Process):
    """Monod uptake → yield-coupled growth, GATED by viability (a dying cell can't grow)."""
    config_schema = {"qmax": _f(1.5), "Ks": _f(0.5), "Y": _f(0.4)}

    def inputs(self):
        return {"nutrient": "float", "biomass": "float", "viability": "float"}

    def outputs(self):
        return {"nutrient": "float", "biomass": "float"}

    def update(self, state, interval):
        N = max(0.0, float(state.get("nutrient", 0.0)))
        X = float(state.get("biomass", 0.0))
        th = float(state.get("viability", 1.0))
        c = self.config
        uptake = (c["qmax"] * N / (c["Ks"] + N)) * X if N > 0 else 0.0
        consumed = min(N, uptake * interval)
        return {"nutrient": -consumed, "biomass": c["Y"] * consumed * th}   # growth scaled by viability


class MembraneStress(Process):
    """A stressor that decays viability at rate k_stress (0 = neutralised)."""
    config_schema = {"k_stress": _f(0.6)}

    def inputs(self):
        return {"viability": "float"}

    def outputs(self):
        return {"viability": "float"}

    def update(self, state, interval):
        th = float(state.get("viability", 1.0))
        dv = -self.config["k_stress"] * th * interval
        return {"viability": max(dv, -th)}
