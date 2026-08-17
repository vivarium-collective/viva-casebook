"""The bounded-cell mechanisms are REAL process-bigraph Processes, and the loop
builds an actual Composite from them — not an inline integrator.

Guards: (1) each mechanism Process registers in the workspace core; (2) a full
composite assembled from all mechanisms runs through the engine and reproduces
the qualitative contract — biomass grows on consumed nutrient (mass balance),
the pool depletes, and viability holds in-band then collapses past tolerance;
(3) the inert draft (no mechanism processes) does NOT grow (the negative control).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def _core():
    import viva_casebook.core as C
    return C.build_core()


def test_mechanism_processes_registered():
    reg = _core().link_registry
    for name in ("TemperatureRamp", "MonodUptake", "YieldGrowth", "ThermalDeath"):
        assert name in reg, f"{name} must register in build_core so composites can address local:{name}"


def _run(active, t_tol=42.0, dt=0.02, t_end=8.0):
    from process_bigraph import Composite
    core = _core()

    def node(a, cfg, i, o):
        return {"_type": "process", "address": "local:" + a, "config": cfg,
                "inputs": i, "outputs": o, "interval": dt}

    st = {"nutrient": 10.0, "biomass": 0.5, "viability": 1.0, "temperature": 37.0, "uptake_flux": 0.0,
          "ramp": node("TemperatureRamp", {"t_start": 37.0, "t_end": 50.0, "duration": t_end},
                       {"temperature": ["temperature"]}, {"temperature": ["temperature"]})}
    if "monod_uptake" in active:
        st["monod"] = node("MonodUptake", {"qmax": 3.0, "Ks": 0.02},
                           {"nutrient": ["nutrient"], "biomass": ["biomass"], "uptake_flux": ["uptake_flux"]},
                           {"nutrient": ["nutrient"], "uptake_flux": ["uptake_flux"]})
    if "yield_growth" in active:
        st["growth"] = node("YieldGrowth", {"Y": 0.45}, {"uptake_flux": ["uptake_flux"]}, {"biomass": ["biomass"]})
    if "thermal_death" in active:
        st["thermal"] = node("ThermalDeath", {"t_tol": t_tol, "k_death": 0.8},
                             {"temperature": ["temperature"], "viability": ["viability"]}, {"viability": ["viability"]})
    sim = Composite({"state": st}, core=core)
    n = int(round(t_end / dt))
    hist = []
    for _ in range(n + 1):
        hist.append({k: float(sim.state.get(k, 0.0)) for k in ("biomass", "nutrient", "viability", "temperature")})
        sim.run(dt)
    return hist


def test_full_composite_reproduces_the_contract():
    h = _run({"monod_uptake", "yield_growth", "thermal_death"}, t_tol=42.0)
    end = h[-1]
    # biomass grows on consumed nutrient (mass balance ΔX ≈ Y·ΔN, Y=0.45, ΔN≈10 → ΔX≈4.5)
    assert end["biomass"] >= 4.5, end["biomass"]
    assert abs((end["biomass"] - 0.5) - 0.45 * (10.0 - end["nutrient"])) <= 0.25
    assert end["nutrient"] <= 0.1                      # pool depleted
    i3 = int(3.0 / 0.02)
    assert h[i3]["viability"] >= 0.9                   # in-band (T<42) viability holds
    assert end["viability"] <= 0.1                     # collapses past tolerance
    assert abs(end["temperature"] - 50.0) < 0.5        # ramp reaches 50 °C


def test_inert_draft_does_not_grow():
    h = _run(set())     # no mechanism processes — the negative control
    assert abs(h[-1]["biomass"] - 0.5) < 1e-6, "inert draft must not grow (control must fail growth)"
