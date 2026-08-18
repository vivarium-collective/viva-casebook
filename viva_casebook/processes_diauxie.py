"""Diauxic growth mechanisms as real process-bigraph Processes.

Two substrates (glucose, lactose), each with a Monod uptake that also grows
biomass at a fixed yield. The twist is REGULATORY: lactose uptake is gated by a
`lac_repression` store (default 1.0 = fully active). Installing `LactoseUptake`
alone lets the cell eat lactose from t=0 — simultaneously with glucose, which is
the WRONG phenotype. Installing `CataboliteRepression` sets `lac_repression` from
the glucose level (a Hill switch), so lactose uptake stays off until glucose is
gone: the diauxic shift, with its growth lag.

The point: fixing the diauxic-order failure is not a knob and not a mechanism the
failing test names — it requires recognizing that a repression COUPLING between
glucose and lactose uptake is needed. A margin-hill-climber can't reach that; it
takes reasoning about the biology.
"""
from __future__ import annotations

from process_bigraph import Process


def _f(default):
    return {"_type": "float", "_default": default}


class GlucoseUptake(Process):
    """Monod uptake of glucose; grows biomass at yield Y."""
    config_schema = {"Vg": _f(2.0), "Kg": _f(0.5), "Y": _f(0.45)}

    def inputs(self):
        return {"glucose": "float", "biomass": "float"}

    def outputs(self):
        return {"glucose": "float", "biomass": "float", "glu_flux": "float"}

    def update(self, state, interval):
        G = max(0.0, float(state.get("glucose", 0.0)))
        X = float(state.get("biomass", 0.0))
        c = self.config
        q = c["Vg"] * G / (c["Kg"] + G) if G > 0 else 0.0
        uptake = q * X
        consumed = min(G, uptake * interval)
        return {"glucose": -consumed, "biomass": c["Y"] * consumed,
                "glu_flux": uptake - float(state.get("glu_flux", 0.0))}


class LactoseUptake(Process):
    """Monod uptake of lactose, GATED by `lac_repression` (default 1.0 = active);
    grows biomass at yield Y."""
    config_schema = {"Vl": _f(2.0), "Kl": _f(0.5), "Y": _f(0.45)}

    def inputs(self):
        return {"lactose": "float", "biomass": "float", "lac_repression": "float"}

    def outputs(self):
        return {"lactose": "float", "biomass": "float", "lac_flux": "float"}

    def update(self, state, interval):
        L = max(0.0, float(state.get("lactose", 0.0)))
        X = float(state.get("biomass", 0.0))
        r = float(state.get("lac_repression", 1.0))
        c = self.config
        q = (c["Vl"] * L / (c["Kl"] + L)) * r if L > 0 else 0.0
        uptake = q * X
        consumed = min(L, uptake * interval)
        return {"lactose": -consumed, "biomass": c["Y"] * consumed,
                "lac_flux": uptake - float(state.get("lac_flux", 0.0))}


class CataboliteRepression(Process):
    """Sets `lac_repression` from glucose via a Hill switch: ~0 while glucose is
    high (lactose uptake off), ~1 once glucose is depleted."""
    config_schema = {"Ki": _f(0.5), "n": _f(4.0)}

    def inputs(self):
        return {"glucose": "float", "lac_repression": "float"}

    def outputs(self):
        return {"lac_repression": "float"}

    def update(self, state, interval):
        G = max(0.0, float(state.get("glucose", 0.0)))
        c = self.config
        Kn = c["Ki"] ** c["n"]
        r = Kn / (Kn + G ** c["n"]) if (Kn + G ** c["n"]) > 0 else 1.0
        return {"lac_repression": r - float(state.get("lac_repression", 1.0))}
