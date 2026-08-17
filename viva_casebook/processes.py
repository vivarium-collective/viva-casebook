"""Bounded-cell mechanisms as real process-bigraph Processes.

Each mechanism is a separate :class:`~process_bigraph.Process` wired to shared
float stores (nutrient, biomass, viability, temperature, uptake_flux). The
model-building loop composes a Composite by INSTALLING these processes one at a
time — "install a mechanism" literally means adding its process node to the
composite document — so the model the loop builds is a genuine process-bigraph
composite run through the engine, not an inline integrator.

Ports are plain ``float`` (base type) so the workspace core needs no extra type
registration. Instantaneous quantities (temperature, uptake_flux) use SET
semantics via ``_set`` over process-bigraph's accumulate-by-default; the pools
(nutrient, biomass, viability) take additive deltas.
"""
from __future__ import annotations

from process_bigraph import Process


def _f(default):
    return {"_type": "float", "_default": default}


# For a store this process EXCLUSIVELY sets (an instantaneous quantity), read
# the current value and emit (target − current) so the additive apply lands
# exactly on `target` regardless of the store's initial value.
class TemperatureRamp(Process):
    """Drives the temperature store on a linear ramp t_start → t_end over `duration`."""
    config_schema = {"t_start": _f(37.0), "t_end": _f(50.0), "duration": _f(8.0)}

    def inputs(self):
        return {"temperature": "float"}

    def outputs(self):
        return {"temperature": "float"}

    def update(self, state, interval):
        self._t = getattr(self, "_t", 0.0) + interval
        c = self.config
        frac = min(self._t, c["duration"]) / c["duration"]
        target = c["t_start"] + (c["t_end"] - c["t_start"]) * frac
        return {"temperature": target - float(state.get("temperature", 0.0))}


class MonodUptake(Process):
    """Biomass-coupled Monod uptake: consumes nutrient at q(N)·biomass and
    publishes the uptake flux for a growth process to convert."""
    config_schema = {"qmax": _f(3.0), "Ks": _f(0.02)}

    def inputs(self):
        return {"nutrient": "float", "biomass": "float", "uptake_flux": "float"}

    def outputs(self):
        return {"nutrient": "float", "uptake_flux": "float"}

    def update(self, state, interval):
        N = max(0.0, float(state.get("nutrient", 0.0)))
        X = float(state.get("biomass", 0.0))
        c = self.config
        q = c["qmax"] * N / (c["Ks"] + N) if N > 0 else 0.0
        uptake = q * X
        consumed = min(N, uptake * interval)         # never drive nutrient negative
        return {"nutrient": -consumed, "uptake_flux": uptake - float(state.get("uptake_flux", 0.0))}


class YieldGrowth(Process):
    """Converts the uptake flux into biomass at a fixed yield (mass-conserving)."""
    config_schema = {"Y": _f(0.45)}

    def inputs(self):
        return {"uptake_flux": "float"}

    def outputs(self):
        return {"biomass": "float"}

    def update(self, state, interval):
        flux = float(state.get("uptake_flux", 0.0))
        return {"biomass": self.config["Y"] * flux * interval}


class ThermalDeath(Process):
    """Viability collapses at a rate proportional to excess temperature above a
    tolerance (threshold-linear thermal death)."""
    config_schema = {"t_tol": _f(35.0), "k_death": _f(0.8)}

    def inputs(self):
        return {"temperature": "float", "viability": "float"}

    def outputs(self):
        return {"viability": "float"}

    def update(self, state, interval):
        T = float(state.get("temperature", 0.0))
        v = float(state.get("viability", 0.0))
        c = self.config
        dv = -c["k_death"] * max(0.0, T - c["t_tol"]) * v * interval
        return {"viability": max(dv, -v)}          # viability floors at 0
