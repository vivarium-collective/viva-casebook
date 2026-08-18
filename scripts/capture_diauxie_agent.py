"""Capture the LLM-agent-driven build of the DIAUXIE study.

Verbatim decisions from a live Claude Sonnet agent that saw only the contract, a
functional description of the mechanism library (NOT the fix), and the graded
verdicts each turn — the same task the deterministic policy GAVE UP on. Replays
the decisions through the real composite (every verdict is engine output),
records them via loop_state with per-test verdicts, and writes the trajectory.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import diauxie_demo as D
from viva_superpowers import loop_state as ls

OUT = D.OUT

DECISIONS = [
    {"action": "install", "mechanism": "glucose_uptake",
     "reasoning": "Install glucose_uptake first since nothing consumes glucose or grows biomass yet, "
                  "and lactose uptake/repression are moot without a glucose signal to react to."},
    {"action": "install", "mechanism": "lactose_uptake",
     "reasoning": "Install lactose_uptake so lactose gets consumed and contributes to biomass growth "
                  "past the 8.0 threshold (anticipating diauxic-order may regress until repression is added)."},
    {"action": "install", "mechanism": "catabolite_repression",
     "reasoning": "Lactose is consumed simultaneously because lac_repression is stuck at 1.0; install "
                  "catabolite_repression so it suppresses lactose uptake while glucose is present, "
                  "enforcing the diauxic sequential order."},
]


def main():
    active, states = set(), [set()]
    for d in DECISIONS:
        active = set(active)
        active.add(d["mechanism"])
        states.append(set(active))

    st = ls.create(D.ROOT, "diauxie-agent", D.QUESTION, max_iterations=12)
    _locked = [{"name": t[0], "pass_if": {"op": t[2].op, "value": t[2].value}} for t in D.TESTS]
    st = ls.lock_tests(st, _locked)

    iterations, prev = [], {}
    for i, act in enumerate(states):
        axes = D.grade(D.simulate(act, {}))
        n_pass = sum(a["verdict"] == "within_tol" for a in axes)
        passing = {a["id"]: a["verdict"] == "within_tol" for a in axes}
        newly = [] if i == 0 else [k for k in passing if passing[k] and not prev.get(k, False)]
        regressed = [k for k in passing if not passing[k] and prev.get(k, False)]
        tests = [{"name": a["id"], "verdict": a["verdict"], "margin": a.get("margin")} for a in axes]
        decision = DECISIONS[i] if i < len(DECISIONS) else {"action": "done",
                   "reasoning": "All four hard tests read within_tol — glucose then lactose, sequentially — so the diauxic model is built."}
        if i > 0:
            pd = DECISIONS[i - 1]
            st = ls.record_iteration(st, edit=pd["reasoning"], target=pd["mechanism"],
                                     margin_deltas={a["id"]: a.get("margin") for a in axes},
                                     gate="pass" if n_pass == len(D.TESTS) else "fail", tests=tests)
        iterations.append({"iteration": i, "active": sorted(act), "n_pass": n_pass, "n_hard": len(D.TESTS),
                           "agent_decision": decision, "newly_fixed": newly, "regressed": regressed,
                           "tests": [{"id": a["id"], "label": D.BY[a["id"]][1], "verdict": a["verdict"],
                                      "observed": a["detail"]["observed"], "expected": D.exp_str(a["id"]),
                                      "margin": a.get("margin"), "severity": "hard"} for a in axes]})
        prev = passing

    done = iterations[-1]["n_pass"] == len(D.TESTS)
    st = ls.advance(st, "DONE" if done else "GIVE_UP", last_verdict={"gate": "pass" if done else "fail"})
    ls.save(D.ROOT, "diauxie-agent", st)

    traj = {"schema": "agent_build_trajectory/v1", "study": "diauxie",
            "driver": "LLM agent (Claude Sonnet) — reasoned each edit from graded verdicts",
            "contract": D.QUESTION,
            "tests": [{"id": t[0], "label": t[1], "expected": D.exp_str(t[0]), "provenance": t[3]} for t in D.TESTS],
            "iterations": iterations,
            "result": {"state": st["state"], "edits": len(DECISIONS), "violations": ls.validate(st, _locked)}}
    with open(os.path.join(OUT, "diauxie_agent_trajectory.json"), "w") as fh:
        json.dump(traj, fh, indent=2)
    print("LLM-AGENT on diauxie:")
    for it in iterations:
        d = it["agent_decision"]
        act = "DONE" if d["action"] == "done" else d["action"] + ":" + (d.get("mechanism") or "")
        fx = f" +{it['newly_fixed']}" if it["newly_fixed"] else ""
        rg = f" REGRESSED {it['regressed']}" if it["regressed"] else ""
        print(f"  iter {it['iteration']} {it['n_pass']}/{it['n_hard']} {it['active']}{fx}{rg} -> {act}")
    print(f"RESULT: {st['state']} in {len(DECISIONS)} edits")


if __name__ == "__main__":
    main()
