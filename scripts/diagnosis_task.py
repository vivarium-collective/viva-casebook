"""Task #3: ambiguous diagnosis — "biomass is too low", but WHY?

Growth here is GATED by viability: a cell whose membrane is failing dies before
it can grow, so biomass stays low even though uptake and yield are fine. The
low-growth margin alone cannot tell you the cause. The correct fix depends on a
diagnosis you can only make by reading the JOINT observables:

  - nutrient fully consumed  -> uptake is NOT the problem
  - viability crashed to ~0   -> the cell is DYING (membrane failure)

So the fix is `stabilize_membrane`, not `boost_yield`/`boost_uptake`. The
deterministic policy hill-climbs on the worst margin (growth) with the plausible
default map growth->boost_yield; it installs the WRONG mechanism, growth still
fails, and it GIVES UP — a misdiagnosis. The LLM reads the crashed viability and
installs the right fix.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))
import viva_casebook.core as _vc_core
from process_bigraph import Composite
from viva_casebook.processes_diagnosis import CellGrowth, MembraneStress
from viva_superpowers import loop_state as ls

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
OUT = os.path.join(ROOT, "workspace", "investigations", "model-building")

QUESTION = ("A cell's biomass is far below target. Diagnose the cause from the observables and add the "
            "mechanism that fixes it, so the cell both grows (biomass >= 3.0) and stays alive "
            "(viability >= 0.5).")
TESTS = ["growth", "survives"]
MECHANISMS = ["boost_uptake", "boost_yield", "stabilize_membrane"]

_CORE = None


def _core():
    global _CORE
    if _CORE is None:
        _CORE = _vc_core.build_core()
        _CORE.register_link("CellGrowth", CellGrowth)
        _CORE.register_link("MembraneStress", MembraneStress)
    return _CORE


def simulate(active):
    qmax = 3.0 if "boost_uptake" in active else 1.5
    Y = 0.7 if "boost_yield" in active else 0.4
    st = {"biomass": 0.5, "nutrient": 10.0, "viability": 1.0,
          "growth": {"_type": "process", "address": "local:CellGrowth",
                     "config": {"qmax": qmax, "Ks": 0.5, "Y": Y},
                     "inputs": {"nutrient": ["nutrient"], "biomass": ["biomass"], "viability": ["viability"]},
                     "outputs": {"nutrient": ["nutrient"], "biomass": ["biomass"]}, "interval": 1.0}}
    if "stabilize_membrane" not in active:      # base carries the stressor; stabilize REMOVES it
        st["stress"] = {"_type": "process", "address": "local:MembraneStress",
                        "config": {"k_stress": 0.6},
                        "inputs": {"viability": ["viability"]}, "outputs": {"viability": ["viability"]},
                        "interval": 1.0}
    c = Composite({"state": st}, core=_core())
    c.run(12.0)
    r = c.state
    return {"biomass": float(r["biomass"]), "nutrient": float(r["nutrient"]),
            "viability": float(r["viability"])}


def observe(active):
    """The full observable panel the agent reads to DIAGNOSE (not just the pass/fail)."""
    o = simulate(active)
    return {"biomass": o["biomass"], "nutrient_final": o["nutrient"], "viability_final": o["viability"]}


def grade(active):
    o = simulate(active)
    margins = {"growth": o["biomass"] - 3.0, "survives": o["viability"] - 0.5}
    v = {t: ("within_tol" if margins[t] >= 0 else "mismatch") for t in TESTS}
    return v, margins, o


NAIVE_MAP = {"growth": "boost_yield"}   # plausible-but-wrong default: "low biomass -> boost yield".
#   survives has NO mapping — nothing is 'named' stabilize_membrane, and the policy has no
#   observable-joining diagnosis step, so it cannot reach the real cause.


def run_policy():
    active, iterations, prev = set(), [], {}
    st = ls.create(ROOT, "diagnosis-policy", QUESTION, max_iterations=8)
    st = ls.lock_tests(st, [{"name": t, "pass_if": {"op": ">=", "value": 0}} for t in TESTS])
    stall = 0
    prevdec = None
    for step in range(6):
        v, margins, o = grade(active)
        n_pass = sum(x == "within_tol" for x in v.values())
        passing = {t: v[t] == "within_tol" for t in TESTS}
        newly = [] if step == 0 else [k for k in passing if passing[k] and not prev.get(k, False)]
        # worst (most-negative) failing margin
        worst = min((t for t in TESTS if v[t] == "mismatch"), key=lambda t: margins[t], default=None)
        mech = NAIVE_MAP.get(worst)
        if mech and mech not in active:
            decision = {"kind": "install", "mechanism": mech, "for_test": worst,
                        "note": f"worst margin is '{worst}' -> naive map installs {mech}"}
            active = set(active); active.add(mech)
        else:
            decision = {"kind": "blocked", "test": worst,
                        "note": (f"worst margin '{worst}' has no mechanism the policy can name, and its only "
                                 f"mapped fix ({NAIVE_MAP.get('growth')}) is installed yet growth still fails "
                                 "— the policy cannot diagnose from the joint observables")}
            stall += 1
        tests_snap = [{"name": t, "verdict": v[t], "margin": round(margins[t], 3)} for t in TESTS]
        if step > 0:
            st = ls.record_iteration(st, edit=(prevdec or {}).get("note", "edit"), target="model",
                                     margin_deltas={}, gate="pass" if n_pass == len(TESTS) else "fail",
                                     tests=tests_snap)
        iterations.append({"iteration": step, "active": sorted(active), "n_pass": n_pass, "n_hard": len(TESTS),
                           "decision": decision, "newly_fixed": newly, "regressed": [],
                           "observables": {k: round(val, 3) for k, val in observe(active).items()},
                           "tests": [{"id": t, "label": t, "verdict": v[t], "observed": round(o.get(
                               "biomass" if t == "growth" else "viability"), 3),
                               "expected": "within_tol", "margin": round(margins[t], 3)} for t in TESTS]})
        prev, prevdec = passing, decision
        if n_pass == len(TESTS):
            st = ls.advance(st, "DONE", last_verdict={"gate": "pass"})
            return iterations, "DONE", st
        if stall >= 2:
            st = ls.advance(st, "GIVE_UP", last_verdict={"gate": "fail", "reason": decision["note"]})
            return iterations, "GIVE_UP", st
    st = ls.advance(st, "GIVE_UP", last_verdict={"gate": "fail", "reason": "budget exhausted"})
    return iterations, "GIVE_UP", st


def main():
    os.makedirs(OUT, exist_ok=True)
    iterations, outcome, st = run_policy()
    ls.save(ROOT, "diagnosis-policy", st)
    traj = {"schema": "model_build_trajectory/v2", "study": "diagnosis",
            "driver": "deterministic worst-margin policy", "contract": QUESTION,
            "tests": [{"id": t, "label": t, "expected": "within_tol"} for t in TESTS],
            "iterations": iterations, "result": {"state": outcome, "edits": len(iterations) - 1}}
    with open(os.path.join(OUT, "diagnosis_policy_trajectory.json"), "w") as fh:
        json.dump(traj, fh, indent=2)
    print("DETERMINISTIC POLICY on ambiguous-diagnosis task:")
    for it in iterations:
        d = it["decision"]
        act = d.get("mechanism") or d["kind"]
        print(f"  iter {it['iteration']} {it['n_pass']}/{it['n_hard']} {it['active']} "
              f"obs={it['observables']} -> {act}")
    print(f"RESULT: {outcome}")


if __name__ == "__main__":
    main()
