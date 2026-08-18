"""Task #6: couple two models at different scales through a translator step.

Model A (a cell producing a metabolite FLUX) and Model B (a spatial diffusion
FIELD) run in different variables and units. Coupling them requires authoring a
TRANSLATOR that maps the cell's scalar flux to the field's per-grid source with
a unit conversion — which is neither a knob nor a mechanism a failing test names.
The deterministic policy has no "author a translator" move and GIVES UP; the LLM
reasons the interface (and the ÷volume unit conversion that conserves mass).
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import viva_casebook.core as _vc_core
from process_bigraph import Composite
from viva_superpowers import loop_state as ls

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
OUT = os.path.join(ROOT, "workspace", "investigations", "model-building")
N, DT, VOL = 11, 1.0, 2.0
_CORE = None


def _core():
    global _CORE
    if _CORE is None:
        _CORE = _vc_core.build_core()
    return _CORE


def _node(a, cfg, i, o):
    return {"_type": "process", "address": "local:" + a, "config": cfg, "inputs": i, "outputs": o, "interval": DT}


def simulate(active, *, unit_conversion=True):
    st = {"biomass": 0.5, "secretion_flux": 0.0, "field": [0.0] * N, "field_source": [0.0] * N}
    if "cell_metabolism" in active:
        st["cell"] = _node("CellMetabolism", {"k_grow": 0.05, "k_secrete": 0.5, "volume": VOL},
                           {"biomass": ["biomass"], "secretion_flux": ["secretion_flux"]},
                           {"biomass": ["biomass"], "secretion_flux": ["secretion_flux"]})
    if "diffusion_field" in active:
        st["fld"] = _node("DiffusionField", {"D": 0.3, "decay": 0.02},
                          {"field": ["field"], "field_source": ["field_source"]}, {"field": ["field"]})
    if "flux_translator" in active:
        st["tr"] = _node("FluxTranslator", {"grid_n": N, "cell_position": 5, "volume": VOL,
                         "apply_unit_conversion": unit_conversion},
                         {"secretion_flux": ["secretion_flux"]}, {"field_source": ["field_source"]})
    sim = Composite({"state": st}, core=_core())
    sim.run(30)
    return {"field": [float(x) for x in (sim.state.get("field") or [])],
            "field_source": [float(x) for x in (sim.state.get("field_source") or [])],
            "flux": float(sim.state.get("secretion_flux", 0.0))}


def grade(active, *, unit_conversion=True):
    r = simulate(active, unit_conversion=unit_conversion)
    f, src, flux = r["field"], r["field_source"], r["flux"]
    peak = max(f) if f else 0.0
    edge = f[0] if f else 0.0
    v = {
        "cell-active": "within_tol" if flux > 0.1 else "mismatch",
        "field-active": "within_tol" if peak > 0.2 else "mismatch",
        "coupled-gradient": "within_tol" if peak > 2 * max(edge, 0.01) else "mismatch",
        "flux-conserved": "within_tol" if (src and abs(sum(src) * VOL - flux) < 0.1) else "mismatch",
    }
    return v


TESTS = ["cell-active", "field-active", "coupled-gradient", "flux-conserved"]
# the policy's authored map — no entry for the coupled tests (no mechanism is named for them,
# and "author a translator" is not an install the policy can express).
NAIVE_MAP = {"cell-active": "cell_metabolism", "field-active": "diffusion_field"}

QUESTION = ("Couple a cell-scale metabolic model (which produces a metabolite FLUX) to a tissue-scale "
            "spatial DIFFUSION FIELD of that metabolite, so that the cell's secretion sources the field "
            "and a gradient forms around the cell — with mass conserved across the scale interface.")


def env_step(active, unit_conversion=True):
    v = grade(active, unit_conversion=unit_conversion)
    return {"active": sorted(active), "unit_conversion": unit_conversion,
            "n_pass": sum(x == "within_tol" for x in v.values()), "n_hard": len(TESTS),
            "all_pass": all(x == "within_tol" for x in v.values()),
            "tests": [{"name": t, "verdict": v[t]} for t in TESTS]}


def run_policy():
    active = set()
    iterations, prev = [], {}
    st = ls.create(ROOT, "multiscale-policy", QUESTION, max_iterations=8)
    st = ls.lock_tests(st, [{"name": t, "pass_if": {"op": ">=", "value": 1}} for t in TESTS])
    stall = 0
    for step in range(8):
        v = grade(active)
        n_pass = sum(x == "within_tol" for x in v.values())
        passing = {t: v[t] == "within_tol" for t in TESTS}
        newly = [] if step == 0 else [k for k in passing if passing[k] and not prev.get(k, False)]
        fails = [t for t in TESTS if v[t] == "mismatch"]
        mech = next((NAIVE_MAP[t] for t in fails if t in NAIVE_MAP and NAIVE_MAP[t] not in active), None)
        if mech:
            decision = {"kind": "install", "mechanism": mech, "test": next(t for t in fails if NAIVE_MAP.get(t) == mech)}
        else:
            decision = {"kind": "blocked", "test": fails[0] if fails else None,
                        "note": "no mechanism is named for `coupled-gradient`/`flux-conserved`, and 'author a "
                                "translator between the two scales' is not an install — the policy has no move"}
        tests_snap = [{"name": t, "verdict": v[t], "margin": None} for t in TESTS]
        if step > 0:
            st = ls.record_iteration(st, edit=(prevdec or {}).get("mechanism") or (prevdec or {}).get("note", "edit"),
                                     target="model", margin_deltas={}, gate="pass" if n_pass == len(TESTS) else "fail", tests=tests_snap)
        iterations.append({"iteration": step, "active": sorted(active), "n_pass": n_pass, "n_hard": len(TESTS),
                           "decision": decision, "newly_fixed": newly, "regressed": [],
                           "tests": [{"id": t, "label": t, "verdict": v[t], "observed": v[t], "expected": "within_tol", "margin": None} for t in TESTS]})
        prev, prevdec = passing, decision
        if decision["kind"] == "install":
            active = set(active); active.add(decision["mechanism"]); stall = 0
        else:
            stall += 1
            if stall >= 2:
                st = ls.advance(st, "GIVE_UP", last_verdict={"gate": "fail", "reason": decision["note"]})
                return iterations, "GIVE_UP", st
        if n_pass == len(TESTS):
            st = ls.advance(st, "DONE", last_verdict={"gate": "pass"}); return iterations, "DONE", st
    st = ls.advance(st, "GIVE_UP", last_verdict={"gate": "fail", "reason": "budget exhausted"})
    return iterations, "GIVE_UP", st


def main():
    os.makedirs(OUT, exist_ok=True)
    iterations, outcome, st = run_policy()
    ls.save(ROOT, "multiscale-policy", st)
    traj = {"schema": "model_build_trajectory/v2", "study": "multiscale", "driver": "deterministic worst-margin policy",
            "contract": QUESTION, "tests": [{"id": t, "label": t, "expected": "within_tol"} for t in TESTS],
            "iterations": iterations, "result": {"state": outcome, "edits": len(iterations) - 1}}
    with open(os.path.join(OUT, "multiscale_policy_trajectory.json"), "w") as fh:
        json.dump(traj, fh, indent=2)
    print("DETERMINISTIC POLICY on multiscale-coupling task:")
    for it in iterations:
        d = it["decision"]
        act = d["kind"] + (":" + d["mechanism"] if d["kind"] == "install" else "")
        print(f"  iter {it['iteration']} {it['n_pass']}/{it['n_hard']} {it['active']} -> {act}")
    print(f"RESULT: {outcome}")
    if outcome == "GIVE_UP":
        print(f"  stuck: {iterations[-1]['decision'].get('note','')}")


if __name__ == "__main__":
    main()
