"""Turn a live agent run (`<task>_agent_live.json`) into a render-compatible
trajectory so the published comparison page shows the REAL agent's reasoning +
real per-test verdicts instead of a hardcoded transcript.

The live JSON records each `step`'s installed set + the agent's reasoning. The
environment is deterministic, so we re-grade each step to recover full per-test
verdicts, and emit an `agent_build_trajectory/v1` doc (the shape the comparison
renderer already consumes). Writes `<task>_agent_live_trajectory.json`.
"""
import json
import os
import sys
import warnings

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(__file__))
import agent_env as E  # noqa: E402

OUT = os.path.join(os.path.dirname(__file__), os.pardir, "workspace", "investigations", "model-building")


def convert(task):
    live = json.load(open(os.path.join(OUT, f"{task}_agent_live.json")))
    contract, mechs, step = E.env_for(task)
    run = live["runs"][0]                       # the in-session run
    # the sequence of builds: a leading empty draft, then each step's active set
    builds = [[]] + [s["active"] for s in run["steps"]]
    reasonings = [None] + [s.get("reasoning") for s in run["steps"]]
    iterations, prev = [], {}
    test_ids = None
    for i, active in enumerate(builds):
        tests, npass, nhard = step(active)
        if test_ids is None:
            test_ids = [t["test"] for t in tests]
        passing = {t["test"]: t["verdict"] == "within_tol" for t in tests}
        newly = [] if i == 0 else [k for k in passing if passing[k] and not prev.get(k, False)]
        regressed = [k for k in passing if not passing[k] and prev.get(k, False)]
        if i < len(builds) - 1:
            dec = {"action": "install", "reasoning": reasonings[i + 1] or ""}
        else:
            dec = {"action": "done", "reasoning": run.get("runs", run).get("final_note", "")
                   if isinstance(run, dict) else ""}
        iterations.append({
            "iteration": i, "active": sorted(active), "n_pass": npass, "n_hard": nhard,
            "agent_decision": dec, "newly_fixed": newly, "regressed": regressed,
            "tests": [{"id": t["test"], "label": t["test"], "verdict": t["verdict"],
                       "observed": t.get("observed", t.get("state_separation", t.get("margin"))),
                       "expected": t.get("expected", "within_tol"), "margin": t.get("margin"),
                       "severity": "hard"} for t in tests],
        })
        prev = passing
    final_note = run["steps"][-1].get("final_note") if run["steps"] and "final_note" in run["steps"][-1] \
        else live.get("runs", [{}])[0].get("final_note", "")
    traj = {
        "schema": "agent_build_trajectory/v1", "study": task,
        "driver": f"LLM agent — LIVE ({live.get('model','?')}), reasoned each build from the env verdicts",
        "contract": contract,
        "tests": [{"id": tid, "label": tid, "expected": "within_tol"} for tid in test_ids],
        "iterations": iterations,
        "result": {"state": run["state"], "edits": run.get("edits", len(run["steps"])), "violations": []},
    }
    path = os.path.join(OUT, f"{task}_agent_live_trajectory.json")
    json.dump(traj, open(path, "w"), indent=2)
    print(f"{task}: live -> {os.path.basename(path)} ({run['state']}, {len(iterations)} iters)")


if __name__ == "__main__":
    for t in ("diauxie", "diagnosis", "bistable"):
        convert(t)
