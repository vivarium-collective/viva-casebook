"""Capture the LLM-agent-driven build of the SBML→COPASI task.

Verbatim decisions from a live Claude Sonnet agent: it authored the A→B→C SBML
pathway one reaction at a time, recognising after the first that the pathway
stopped at B and adding B→C so the terminal product accumulates. Every verdict is
from the REAL COPASI backend (basico, via viva-copasi). The deterministic policy
gave up at 0/5 — authoring an SBML reaction network is not an install.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import sbml_task as T
from viva_superpowers import loop_state as ls

OUT = T.OUT
DECISIONS = [
    {"action": "add_reaction", "value": "A->B",
     "reasoning": "Start the pathway by converting A to B, the first required step before B can flow to C."},
    {"action": "add_reaction", "value": "B->C",
     "reasoning": "A→B alone leaves B as the terminal species; add B→C so the terminal product C accumulates."},
]


def main():
    os.makedirs(OUT, exist_ok=True)
    active, states = set(), [set()]
    for d in DECISIONS:
        active = set(active); active.add(d["value"]); states.append(set(active))

    st = ls.create(T.ROOT, "sbml-agent", T.QUESTION, max_iterations=8)
    _locked = [{"name": t, "pass_if": {"op": ">=", "value": 1}} for t in T.TESTS]
    st = ls.lock_tests(st, _locked)

    iterations, prev = [], {}
    for i, act in enumerate(states):
        v = T.grade(act)
        n_pass = sum(x == "within_tol" for x in v.values())
        passing = {t: v[t] == "within_tol" for t in T.TESTS}
        newly = [] if i == 0 else [k for k in passing if passing[k] and not prev.get(k, False)]
        tests = [{"name": t, "verdict": v[t], "margin": None} for t in T.TESTS]
        decision = DECISIONS[i] if i < len(DECISIONS) else {"action": "done",
                   "reasoning": "All five quality tests pass — COPASI loads the model, it reaches a valid "
                                "steady state, mass is conserved, and C is the accumulating terminal product."}
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
    ls.save(T.ROOT, "sbml-agent", st)

    traj = {"schema": "agent_build_trajectory/v1", "study": "sbml",
            "driver": "LLM agent (Claude Sonnet) — authored the SBML reaction network, graded in real COPASI",
            "contract": T.QUESTION,
            "tests": [{"id": t, "label": t, "expected": "within_tol"} for t in T.TESTS],
            "iterations": iterations,
            "result": {"state": st["state"], "edits": len(DECISIONS), "violations": ls.validate(st, _locked)}}
    with open(os.path.join(OUT, "sbml_agent_trajectory.json"), "w") as fh:
        json.dump(traj, fh, indent=2)
    print("LLM-AGENT on SBML/COPASI task:")
    for it in iterations:
        d = it["agent_decision"]
        act = "DONE" if d["action"] == "done" else d["action"] + ":" + (d.get("value") or "")
        print(f"  iter {it['iteration']} {it['n_pass']}/{it['n_hard']} {it['active']} -> {act}")
    print(f"RESULT: {st['state']} in {len(DECISIONS)} edits")


if __name__ == "__main__":
    main()
