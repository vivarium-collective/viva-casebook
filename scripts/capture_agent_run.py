"""Capture the REAL LLM-agent-driven build of the bounded-cell study.

The decisions below are verbatim from an actual LLM agent (Claude Sonnet) driving
the loop through scripts/agent_step.py — it saw only the contract, a functional
description of the mechanism library (NOT the test→mechanism map), and the graded
verdicts each turn, and reasoned out each edit. This script replays those exact
decisions through the same environment (so every verdict here is the real engine
output), records them via viva_superpowers.loop_state WITH per-test verdicts
(lighting up the workbench Build matrix), and writes agent_trajectory.json.

It is the agent-driven counterpart to build_loop_demo.py's deterministic policy —
same study, same real composite, decisions by an LLM instead of a coded rule.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import build_loop_demo as B
from viva_superpowers import loop_state as ls

ROOT = B.ROOT
OUT = B.OUT
LOOP_STUDY = "bounded-cell-agent"

# The agent's actual decisions + verbatim reasoning (from the live run).
DECISIONS = [
    {"action": "install", "mechanism": "monod_uptake",
     "reasoning": "Growth and nutrient-depletion both require consuming nutrient via a Monod uptake "
                  "flux before biomass conversion can happen, and monod_uptake is the upstream "
                  "dependency yield_growth needs, so install it first."},
    {"action": "install", "mechanism": "yield_growth",
     "reasoning": "Conservation and growth are both failing because the uptake flux from monod_uptake "
                  "has nowhere to go — yield_growth converts consumed nutrient into biomass, closing "
                  "the mass balance."},
    {"action": "install", "mechanism": "thermal_death",
     "reasoning": "viability-cliff requires viability to collapse once temperature exceeds tolerance, "
                  "which is exactly what thermal_death models and no mechanism for that is installed yet."},
    {"action": "calibrate", "knob": "t_tol", "value": 43.0,
     "reasoning": "t_tol=35 is below the starting temperature so decay starts at t=0 and kills viability "
                  "before t=3h; raising t_tol above the t=3h temperature (~42 °C) delays onset past the "
                  "in-band checkpoint while still collapsing viability before the 50 °C peak."},
]


def grade_state(active, knobs):
    out = B.simulate(active, knobs)
    axes = B.grade(out)
    hard = [t["id"] for t in B.TESTS if t["sev"] == "hard"]
    verd = {a["id"]: a for a in axes}
    n_pass = sum(verd[h]["verdict"] == "within_tol" for h in hard)
    tests = [{"name": a["id"], "verdict": a["verdict"],
              "margin": (round(a["margin"], 4) if a.get("margin") is not None else None),
              "observed": a["detail"]["observed"], "severity": a.get("severity")} for a in axes]
    return n_pass, len(hard), tests


def main():
    os.makedirs(OUT, exist_ok=True)
    active, knobs = set(), {}
    # cumulative states: draft, then after each decision
    states = [(set(), {})]
    for d in DECISIONS:
        active = set(active)
        knobs = dict(knobs)
        if d["action"] == "install":
            active.add(d["mechanism"])
            knobs.update(B.LIBRARY[d["mechanism"]]["knobs"])
        elif d["action"] == "calibrate":
            knobs[d["knob"]] = d["value"]
        states.append((set(active), dict(knobs)))

    st = ls.create(ROOT, LOOP_STUDY, B.QUESTION, max_iterations=12)
    st = ls.lock_tests(st, B.build_spec()["behavior_tests"])

    iterations, prev = [], {}
    for i, (act, kn) in enumerate(states):
        n_pass, n_hard, tests = grade_state(act, kn)
        passing = {t["name"]: (t["verdict"] == "within_tol") for t in tests if t["severity"] == "hard"}
        newly = [] if i == 0 else [k for k in passing if passing[k] and not prev.get(k, False)]
        regressed = [k for k in passing if not passing[k] and prev.get(k, False)]
        decision = DECISIONS[i] if i < len(DECISIONS) else {"action": "done", "reasoning":
                   "All five hard tests read within_tol — the model is built; report DONE rather than edit further."}
        edit = ("DRAFT — inert composite" if i == 0 else
                (decision["reasoning"] if i - 1 < len(DECISIONS) else "done"))
        # record via loop_state with per-test verdicts (i>0 are real edits)
        if i > 0:
            prevd = DECISIONS[i - 1]
            st = ls.record_iteration(
                st, edit=prevd["reasoning"],
                target=prevd.get("mechanism") or prevd.get("knob") or "model",
                margin_deltas={t["name"]: t["margin"] for t in tests if t["margin"] is not None},
                gate="pass" if n_pass == n_hard else "fail",
                tests=[{"name": t["name"], "verdict": t["verdict"], "margin": t["margin"]} for t in tests])
        iterations.append({
            "iteration": i, "active": sorted(act), "knobs": {k: round(v, 3) for k, v in kn.items()},
            "n_pass": n_pass, "n_hard": n_hard,
            "agent_decision": decision, "newly_fixed": newly, "regressed": regressed,
            "tests": tests,
        })
        prev = passing

    done = iterations[-1]["n_pass"] == iterations[-1]["n_hard"]
    st = ls.advance(st, "DONE" if done else "GIVE_UP", last_verdict={"gate": "pass" if done else "fail"})
    violations = ls.validate(st, B.build_spec()["behavior_tests"])
    ls.save(ROOT, LOOP_STUDY, st)

    traj = {
        "schema": "agent_build_trajectory/v1",
        "study": LOOP_STUDY,
        "driver": "LLM agent (Claude Sonnet) — decisions reasoned live from graded verdicts",
        "contract": B.QUESTION,
        "iterations": iterations,
        "result": {"state": st["state"], "edits_to_pass": len(DECISIONS),
                   "violations": violations, "final_knobs": iterations[-1]["knobs"]},
        "vs_deterministic": {"agent_edits": len(DECISIONS), "policy_edits": 5,
                             "note": "the agent reached a full pass in 4 edits vs the deterministic "
                                     "policy's 5 — it computed the thermal tolerance in one calibration "
                                     "step (t_tol=43) instead of two blind steps (35→38.5→42)."},
    }
    path = os.path.join(OUT, "agent_trajectory.json")
    with open(path, "w") as fh:
        json.dump(traj, fh, indent=2)

    print(f"LLM-agent build of '{LOOP_STUDY}':")
    for it in iterations:
        d = it["agent_decision"]
        act = (d["action"] + ":" + (d.get("mechanism") or d.get("knob") or "")) if d["action"] != "done" else "DONE"
        fx = f" +{it['newly_fixed']}" if it["newly_fixed"] else ""
        rg = f" REGRESSED {it['regressed']}" if it["regressed"] else ""
        print(f"  iter {it['iteration']} {it['n_pass']}/{it['n_hard']} {it['active']}{fx}{rg} -> {act}")
    print(f"RESULT: {st['state']} in {len(DECISIONS)} edits; violations={violations}")
    print(f"loop_state -> .pbg/loop/{LOOP_STUDY}.json (per-test verdicts recorded)")
    print(f"trajectory -> {os.path.relpath(path, ROOT)}")


if __name__ == "__main__":
    main()
