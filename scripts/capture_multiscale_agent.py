"""Capture the LLM-agent-driven build of the MULTISCALE-COUPLING task.

Verbatim decisions from a live Claude Sonnet agent: it installed the two models,
recognised they were decoupled (cell writes a scalar flux, field reads a per-grid
source), and AUTHORED a translator with the unit conversion (mol/time → mM/time
over the compartment volume) needed for mass to conserve. The deterministic
policy gave up at 1/4 — it has no 'author a translator' move.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import multiscale_task as T
from viva_superpowers import loop_state as ls

OUT = T.OUT

DECISIONS = [
    {"action": "install", "value": "cell_metabolism",
     "reasoning": "Start with the cell-scale source model before anything can secrete."},
    {"action": "install", "value": "diffusion_field",
     "reasoning": "The tissue-scale field must exist before it can respond."},
    {"action": "author_translator", "value": "flux_translator", "unit_conversion": True,
     "reasoning": "The two models are unconnected until a translator maps secretion_flux to field_source; "
                  "units differ (mol/time vs mM/time over volume V=2.0) so the conversion must be applied "
                  "for mass to conserve across the interface."},
]


def main():
    os.makedirs(OUT, exist_ok=True)
    active, states = set(), [(set(), True)]
    uc = True
    for d in DECISIONS:
        active = set(active)
        active.add("flux_translator" if d["action"] == "author_translator" else d["value"])
        if d["action"] == "author_translator":
            uc = d.get("unit_conversion", True)
        states.append((set(active), uc))

    st = ls.create(T.ROOT, "multiscale-agent", T.QUESTION, max_iterations=8)
    _locked = [{"name": t, "pass_if": {"op": ">=", "value": 1}} for t in T.TESTS]
    st = ls.lock_tests(st, _locked)

    iterations, prev = [], {}
    for i, (act, u) in enumerate(states):
        v = T.grade(act, unit_conversion=u)
        n_pass = sum(x == "within_tol" for x in v.values())
        passing = {t: v[t] == "within_tol" for t in T.TESTS}
        newly = [] if i == 0 else [k for k in passing if passing[k] and not prev.get(k, False)]
        tests = [{"name": t, "verdict": v[t], "margin": None} for t in T.TESTS]
        decision = DECISIONS[i] if i < len(DECISIONS) else {"action": "done",
                   "reasoning": "All four tests pass — the translator couples the two scales and conserves mass."}
        if i > 0:
            pd = DECISIONS[i - 1]
            st = ls.record_iteration(st, edit=pd["reasoning"], target=pd["value"], margin_deltas={},
                                     gate="pass" if n_pass == len(T.TESTS) else "fail", tests=tests)
        iterations.append({"iteration": i, "active": sorted(act), "n_pass": n_pass, "n_hard": len(T.TESTS),
                           "agent_decision": decision, "newly_fixed": newly, "regressed": [],
                           "tests": [{"id": t, "label": t, "verdict": v[t], "observed": v[t],
                                      "expected": "within_tol", "margin": None, "severity": "hard"} for t in T.TESTS]})
        prev = passing

    done = iterations[-1]["n_pass"] == len(T.TESTS)
    st = ls.advance(st, "DONE" if done else "GIVE_UP", last_verdict={"gate": "pass" if done else "fail"})
    ls.save(T.ROOT, "multiscale-agent", st)

    traj = {"schema": "agent_build_trajectory/v1", "study": "multiscale",
            "driver": "LLM agent (Claude Sonnet) — authored the translator + reasoned the unit conversion",
            "contract": T.QUESTION,
            "tests": [{"id": t, "label": t, "expected": "within_tol"} for t in T.TESTS],
            "iterations": iterations,
            "result": {"state": st["state"], "edits": len(DECISIONS), "violations": ls.validate(st, _locked)}}
    with open(os.path.join(OUT, "multiscale_agent_trajectory.json"), "w") as fh:
        json.dump(traj, fh, indent=2)
    print("LLM-AGENT on multiscale-coupling task:")
    for it in iterations:
        d = it["agent_decision"]
        act = "DONE" if d["action"] == "done" else d["action"] + ":" + (d.get("value") or "")
        print(f"  iter {it['iteration']} {it['n_pass']}/{it['n_hard']} {it['active']} -> {act}")
    print(f"RESULT: {st['state']} in {len(DECISIONS)} edits")


if __name__ == "__main__":
    main()
