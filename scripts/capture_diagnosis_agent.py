"""Capture the LLM-agent-driven diagnosis of the low-biomass task.

Verbatim decision from a live Claude agent: shown the observable panel for the
failing base cell — biomass low, nutrient FULLY consumed, viability crashed to 0
— it diagnosed that the cell is DYING (not yield- or uptake-limited) and
installed `stabilize_membrane`, passing both tests in one edit. The deterministic
policy misdiagnosed: it installed `boost_yield` off the worst margin, growth
still failed, and it gave up.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import diagnosis_task as T
from viva_superpowers import loop_state as ls

OUT = T.OUT
DECISIONS = [
    {"action": "install_mechanism", "value": "stabilize_membrane",
     "reasoning": "The panel diagnoses the cause: nutrient is fully consumed (uptake is fine) and yield is "
                  "adequate, yet biomass is low BECAUSE viability has crashed to ~0 — the cell dies before it "
                  "can grow. This is membrane failure, not a yield or uptake deficit, so boosting either "
                  "would not help. Install stabilize_membrane to keep the cell alive; growth follows."},
]


def main():
    os.makedirs(OUT, exist_ok=True)
    active, states = set(), [set()]
    for d in DECISIONS:
        active = set(active); active.add(d["value"]); states.append(set(active))

    st = ls.create(T.ROOT, "diagnosis-agent", T.QUESTION, max_iterations=8)
    st = ls.lock_tests(st, [{"name": t, "pass_if": {"op": ">=", "value": 0}} for t in T.TESTS])

    iterations, prev = [], {}
    for i, act in enumerate(states):
        v, margins, o = T.grade(act)
        n_pass = sum(x == "within_tol" for x in v.values())
        passing = {t: v[t] == "within_tol" for t in T.TESTS}
        newly = [] if i == 0 else [k for k in passing if passing[k] and not prev.get(k, False)]
        tests = [{"name": t, "verdict": v[t], "margin": round(margins[t], 3)} for t in T.TESTS]
        decision = DECISIONS[i] if i < len(DECISIONS) else {"action": "done",
                   "reasoning": "Both tests pass — the cell survives (viability held) and grows past the "
                                "biomass target. The diagnosis (membrane failure) was correct."}
        if i > 0:
            pd = DECISIONS[i - 1]
            st = ls.record_iteration(st, edit=pd["reasoning"], target=pd["value"], margin_deltas={},
                                     gate="pass" if n_pass == len(T.TESTS) else "fail", tests=tests)
        iterations.append({"iteration": i, "active": sorted(act), "n_pass": n_pass, "n_hard": len(T.TESTS),
                           "agent_decision": decision, "newly_fixed": newly, "regressed": [],
                           "observables": {k: round(val, 3) for k, val in T.observe(act).items()},
                           "tests": [{"id": t, "label": t, "verdict": v[t],
                                      "observed": round(o.get("biomass" if t == "growth" else "viability"), 3),
                                      "expected": "within_tol", "margin": round(margins[t], 3),
                                      "severity": "hard"} for t in T.TESTS]})
        prev = passing

    done = iterations[-1]["n_pass"] == len(T.TESTS)
    st = ls.advance(st, "DONE" if done else "GIVE_UP", last_verdict={"gate": "pass" if done else "fail"})
    ls.save(T.ROOT, "diagnosis-agent", st)

    traj = {"schema": "agent_build_trajectory/v1", "study": "diagnosis",
            "driver": "LLM agent (Claude) — diagnosed the cause from the joint observable panel",
            "contract": T.QUESTION,
            "tests": [{"id": t, "label": t, "expected": "within_tol"} for t in T.TESTS],
            "iterations": iterations,
            "result": {"state": st["state"], "edits": len(DECISIONS), "violations": ls.validate(st, [])}}
    with open(os.path.join(OUT, "diagnosis_agent_trajectory.json"), "w") as fh:
        json.dump(traj, fh, indent=2)
    print("LLM-AGENT on ambiguous-diagnosis task:")
    for it in iterations:
        d = it["agent_decision"]
        act = "DONE" if d["action"] == "done" else d["action"] + ":" + (d.get("value") or "")
        print(f"  iter {it['iteration']} {it['n_pass']}/{it['n_hard']} {it['active']} "
              f"obs={it['observables']} -> {act}")
    print(f"RESULT: {st['state']} in {len(DECISIONS)} edits")


if __name__ == "__main__":
    main()
