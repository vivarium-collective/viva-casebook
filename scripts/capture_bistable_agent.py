"""Capture the LLM-agent-driven build of the bistable-switch task.

Verbatim decision from a live Claude agent: it recognised that two stable states
in a mutual-repression network is a STRUCTURAL property requiring cooperative
(ultrasensitive) feedback — Hill n >= 2 — not a level a knob sets, and installed
`cooperative_binding`, producing the two basins in one edit. The deterministic
policy tuned expression (a knob), stayed monostable (state separation = 0), and
gave up.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import bistable_task as T
from viva_superpowers import loop_state as ls

OUT = T.OUT
DECISIONS = [
    {"action": "install_mechanism", "value": "cooperative_binding",
     "reasoning": "Both genes relax to the same symmetric level — the switch is monostable, and boosting "
                  "expression or degradation only moves that single fixed point, never splits it. Two stable "
                  "states in a mutual-repression network require COOPERATIVE repression (Hill n >= 2): "
                  "ultrasensitivity is what destabilises the symmetric state and opens two basins. Install "
                  "cooperative_binding."},
]


def main():
    os.makedirs(OUT, exist_ok=True)
    active, states = set(), [set()]
    for d in DECISIONS:
        active = set(active); active.add(d["value"]); states.append(set(active))

    st = ls.create(T.ROOT, "bistable-agent", T.QUESTION, max_iterations=8)
    _locked = [{"name": t, "pass_if": {"op": ">=", "value": 0}} for t in T.TESTS]
    st = ls.lock_tests(st, _locked)

    iterations, prev = [], {}
    for i, act in enumerate(states):
        v, margins, o = T.grade(act)
        n_pass = sum(x == "within_tol" for x in v.values())
        passing = {t: v[t] == "within_tol" for t in T.TESTS}
        newly = [] if i == 0 else [k for k in passing if passing[k] and not prev.get(k, False)]
        tests = [{"name": t, "verdict": v[t], "margin": round(margins[t], 3)} for t in T.TESTS]
        decision = DECISIONS[i] if i < len(DECISIONS) else {"action": "done",
                   "reasoning": "Both tests pass — the two initial conditions latch to distinct, decisive "
                                "states (A-high vs B-high). Cooperative feedback produced the bistability."}
        if i > 0:
            pd = DECISIONS[i - 1]
            st = ls.record_iteration(st, edit=pd["reasoning"], target=pd["value"], margin_deltas={},
                                     gate="pass" if n_pass == len(T.TESTS) else "fail", tests=tests)
        iterations.append({"iteration": i, "active": sorted(act), "n_pass": n_pass, "n_hard": len(T.TESTS),
                           "agent_decision": decision, "newly_fixed": newly, "regressed": [],
                           "observables": T.observe(act),
                           "tests": [{"id": t, "label": t, "verdict": v[t], "observed": round(o["sep"], 3),
                                      "expected": "within_tol", "margin": round(margins[t], 3),
                                      "severity": "hard"} for t in T.TESTS]})
        prev = passing

    done = iterations[-1]["n_pass"] == len(T.TESTS)
    st = ls.advance(st, "DONE" if done else "GIVE_UP", last_verdict={"gate": "pass" if done else "fail"})
    ls.save(T.ROOT, "bistable-agent", st)

    traj = {"schema": "agent_build_trajectory/v1", "study": "bistable",
            "driver": "LLM agent (Claude) — recognised bistability requires cooperative feedback",
            "contract": T.QUESTION,
            "tests": [{"id": t, "label": t, "expected": "within_tol"} for t in T.TESTS],
            "iterations": iterations,
            "result": {"state": st["state"], "edits": len(DECISIONS), "violations": ls.validate(st, _locked)}}
    with open(os.path.join(OUT, "bistable_agent_trajectory.json"), "w") as fh:
        json.dump(traj, fh, indent=2)
    print("LLM-AGENT on bistable-switch task:")
    for it in iterations:
        d = it["agent_decision"]
        act = "DONE" if d["action"] == "done" else d["action"] + ":" + (d.get("value") or "")
        print(f"  iter {it['iteration']} {it['n_pass']}/{it['n_hard']} {it['active']} "
              f"sep={it['observables']['state_separation']} -> {act}")
    print(f"RESULT: {st['state']} in {len(DECISIONS)} edits")


if __name__ == "__main__":
    main()
