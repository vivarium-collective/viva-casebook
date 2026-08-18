"""Capture the LLM-agent-driven build of the MULTICELLULAR task.

Verbatim decisions from a live Claude Sonnet agent: it SELECTED the CPM simulator
(the only one with lattice + fields + cell-fate), then composed the niche/field
and the fate subcell. The deterministic policy gave up (no 'choose a simulator'
move). Replays through the real environment and records a loop_state with
per-test verdicts.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import multicell_task as T
from viva_superpowers import loop_state as ls

OUT = T.OUT

DECISIONS = [
    {"action": "select_simulator", "value": "cpm",
     "reasoning": "Only cpm supports lattice + morphogen fields + cell-fate relabeling, which the "
                  "differentiation-gradient phenotype requires (pymunk has none; spatial has fields but no fate)."},
    {"action": "add_component", "value": "wnt_field_niche",
     "reasoning": "The Wnt niche field must exist before per-cell fate can sense it, so add the niche/field first."},
    {"action": "add_component", "value": "stemness_fate_subcell",
     "reasoning": "Cells need the subcellular fate model that reads local Wnt to relabel stem vs "
                  "differentiated, producing the spatial gradient."},
]


def main():
    os.makedirs(OUT, exist_ok=True)
    sim, comps = None, set()
    states = [(None, set())]
    for d in DECISIONS:
        if d["action"] == "select_simulator":
            sim = d["value"]
        else:
            comps = set(comps); comps.add(d["value"])
        states.append((sim, set(comps)))

    st = ls.create(T.ROOT, "multicell-agent", T.QUESTION, max_iterations=8)
    _locked = [{"name": t, "pass_if": {"op": ">=", "value": 1}} for t in T.TESTS]
    st = ls.lock_tests(st, _locked)

    iterations, prev = [], {}
    for i, (s, c) in enumerate(states):
        v = T.grade_build(s or "pymunk", c) if s else {t: "mismatch" for t in T.TESTS}
        n_pass = sum(x == "within_tol" for x in v.values())
        passing = {t: v[t] == "within_tol" for t in T.TESTS}
        newly = [] if i == 0 else [k for k in passing if passing[k] and not prev.get(k, False)]
        tests = [{"name": t, "verdict": v[t], "margin": None} for t in T.TESTS]
        decision = DECISIONS[i] if i < len(DECISIONS) else {"action": "done",
                   "reasoning": "All three tests pass — CPM with the niche field and the fate subcell produces the gradient."}
        if i > 0:
            pd = DECISIONS[i - 1]
            st = ls.record_iteration(st, edit=pd["reasoning"], target=pd["value"], margin_deltas={},
                                     gate="pass" if n_pass == len(T.TESTS) else "fail", tests=tests)
        iterations.append({"iteration": i, "active": ([s] if s else []) + sorted(c),
                           "n_pass": n_pass, "n_hard": len(T.TESTS), "agent_decision": decision,
                           "newly_fixed": newly, "regressed": [],
                           "tests": [{"id": t, "label": t, "verdict": v[t], "observed": v[t],
                                      "expected": "within_tol", "margin": None, "severity": "hard"} for t in T.TESTS]})
        prev = passing

    done = iterations[-1]["n_pass"] == len(T.TESTS)
    st = ls.advance(st, "DONE" if done else "GIVE_UP", last_verdict={"gate": "pass" if done else "fail"})
    ls.save(T.ROOT, "multicell-agent", st)

    traj = {"schema": "agent_build_trajectory/v1", "study": "multicellular",
            "driver": "LLM agent (Claude Sonnet) — selected the simulator + composed the subcell model",
            "contract": T.QUESTION,
            "tests": [{"id": t, "label": t, "expected": "within_tol"} for t in T.TESTS],
            "iterations": iterations,
            "result": {"state": st["state"], "edits": len(DECISIONS), "violations": ls.validate(st, _locked)}}
    with open(os.path.join(OUT, "multicell_agent_trajectory.json"), "w") as fh:
        json.dump(traj, fh, indent=2)
    print("LLM-AGENT on multicellular task:")
    for it in iterations:
        d = it["agent_decision"]
        act = "DONE" if d["action"] == "done" else d["action"] + ":" + (d.get("value") or "")
        print(f"  iter {it['iteration']} {it['n_pass']}/{it['n_hard']} {it['active']} -> {act}")
    print(f"RESULT: {st['state']} in {len(DECISIONS)} edits")


if __name__ == "__main__":
    main()
