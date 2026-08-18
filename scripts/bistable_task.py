"""Task #4: build a BISTABLE switch (a genetic toggle switch).

The model must have two distinct stable states and latch to whichever gene starts
ahead — a real toggle switch, not a graded response. Bistability only exists when
the mutual repression is COOPERATIVE (Hill exponent n >= 2); with n = 1 the switch
is monostable and every initial condition relaxes to the same symmetric state.

Creating bistability is a STRUCTURAL change (add cooperativity/positive feedback),
not a knob a failing margin names. A worst-margin policy tuning expression or
degradation stays monostable forever and GIVES UP; the LLM recognises that two
basins require cooperative feedback and adds it.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))
import viva_casebook.core as _vc_core
from process_bigraph import Composite
from viva_casebook.processes_bistable import ToggleSwitch
from viva_superpowers import loop_state as ls

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
OUT = os.path.join(ROOT, "workspace", "investigations", "model-building")

QUESTION = ("Build a bistable genetic switch: two mutually repressing genes A and B that settle into two "
            "DISTINCT stable states and latch to whichever gene starts ahead (a decisive toggle, not a "
            "graded midpoint).")
TESTS = ["bistable", "decisive"]
MECHANISMS = ["boost_expression", "add_degradation", "cooperative_binding"]

_CORE = None


def _core():
    global _CORE
    if _CORE is None:
        _CORE = _vc_core.build_core()
        _CORE.register_link("ToggleSwitch", ToggleSwitch)
    return _CORE


def _run(active, A0, B0):
    n = 2.0 if "cooperative_binding" in active else 1.0
    beta = 8.0 if "boost_expression" in active else 4.0
    deg = 1.5 if "add_degradation" in active else 1.0
    st = {"A": A0, "B": B0,
          "sw": {"_type": "process", "address": "local:ToggleSwitch",
                 "config": {"beta": beta, "K": 1.0, "n": n, "deg": deg},
                 "inputs": {"A": ["A"], "B": ["B"]}, "outputs": {"A": ["A"], "B": ["B"]}, "interval": 0.05}}
    c = Composite({"state": st}, core=_core())
    c.run(40.0)
    return float(c.state["A"]), float(c.state["B"])


def observe(active):
    aH = _run(active, 3.0, 0.1)     # A starts ahead
    bH = _run(active, 0.1, 3.0)     # B starts ahead
    return {"A_from_Ahigh": round(aH[0], 3), "B_from_Ahigh": round(aH[1], 3),
            "A_from_Bhigh": round(bH[0], 3), "B_from_Bhigh": round(bH[1], 3),
            "state_separation": round(abs(aH[0] - bH[0]), 3)}


def grade(active):
    aH = _run(active, 3.0, 0.1)
    bH = _run(active, 0.1, 3.0)
    sep = abs(aH[0] - bH[0])
    # decisive: in each basin the winner is high and the loser is low
    decisive = (aH[0] >= 2.5 and aH[1] <= 1.0 and bH[1] >= 2.5 and bH[0] <= 1.0)
    margins = {"bistable": sep - 2.0, "decisive": (min(aH[0], bH[1]) - 2.5) if decisive else -2.5}
    v = {"bistable": "within_tol" if sep >= 2.0 else "mismatch",
         "decisive": "within_tol" if decisive else "mismatch"}
    return v, margins, {"sep": sep, "aH": aH, "bH": bH}


NAIVE_MAP = {"bistable": "boost_expression"}   # plausible-but-wrong: "states not separated -> boost expression".
#   'decisive' is unmapped, and boosting expression on a NON-cooperative switch stays monostable, so the
#   policy never reaches the structural fix (cooperative_binding).


def run_policy():
    active, iterations, prev = set(), [], {}
    st = ls.create(ROOT, "bistable-policy", QUESTION, max_iterations=8)
    st = ls.lock_tests(st, [{"name": t, "pass_if": {"op": ">=", "value": 0}} for t in TESTS])
    stall, prevdec = 0, None
    for step in range(6):
        v, margins, o = grade(active)
        n_pass = sum(x == "within_tol" for x in v.values())
        passing = {t: v[t] == "within_tol" for t in TESTS}
        newly = [] if step == 0 else [k for k in passing if passing[k] and not prev.get(k, False)]
        worst = min((t for t in TESTS if v[t] == "mismatch"), key=lambda t: margins[t], default=None)
        # the policy spends whatever mapped-and-uninstalled move it has before conceding
        actionable = [t for t in TESTS if v[t] == "mismatch"
                      and NAIVE_MAP.get(t) and NAIVE_MAP[t] not in active]
        target = min(actionable, key=lambda t: margins[t]) if actionable else worst
        mech = NAIVE_MAP.get(target)
        worst = target
        if mech and mech not in active:
            decision = {"kind": "install", "mechanism": mech, "for_test": worst,
                        "note": f"worst margin is '{worst}' -> naive map installs {mech}"}
            active = set(active); active.add(mech)
        else:
            decision = {"kind": "blocked", "test": worst,
                        "note": (f"worst margin '{worst}' has no mechanism the policy can name; boosting "
                                 "expression left the switch monostable — the policy has no way to express "
                                 "'add cooperative feedback' (a structural change, not a knob)")}
            stall += 1
        tests_snap = [{"name": t, "verdict": v[t], "margin": round(margins[t], 3)} for t in TESTS]
        if step > 0:
            st = ls.record_iteration(st, edit=(prevdec or {}).get("note", "edit"), target="model",
                                     margin_deltas={}, gate="pass" if n_pass == len(TESTS) else "fail",
                                     tests=tests_snap)
        iterations.append({"iteration": step, "active": sorted(active), "n_pass": n_pass, "n_hard": len(TESTS),
                           "decision": decision, "newly_fixed": newly, "regressed": [],
                           "observables": observe(active),
                           "tests": [{"id": t, "label": t, "verdict": v[t], "observed": round(o["sep"], 3),
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
    ls.save(ROOT, "bistable-policy", st)
    traj = {"schema": "model_build_trajectory/v2", "study": "bistable",
            "driver": "deterministic worst-margin policy", "contract": QUESTION,
            "tests": [{"id": t, "label": t, "expected": "within_tol"} for t in TESTS],
            "iterations": iterations, "result": {"state": outcome, "edits": len(iterations) - 1}}
    with open(os.path.join(OUT, "bistable_policy_trajectory.json"), "w") as fh:
        json.dump(traj, fh, indent=2)
    print("DETERMINISTIC POLICY on bistable-switch task:")
    for it in iterations:
        d = it["decision"]
        print(f"  iter {it['iteration']} {it['n_pass']}/{it['n_hard']} {it['active']} "
              f"sep={it['observables']['state_separation']} -> {d.get('mechanism') or d['kind']}")
    print(f"RESULT: {outcome}")


if __name__ == "__main__":
    main()
