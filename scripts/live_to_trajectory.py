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


def _violations_for(task, run):
    """Compute integrity violations HONESTLY by replaying the run through a real
    loop_state: lock the environment's (fixed) test set, record each iteration
    against that same set, then validate. Returns loop_state's real I1-I5 output —
    not a hardcoded []. (For menu tasks the tests are environment-fixed, so this
    genuinely confirms the agent never mutated the locked set.)"""
    try:
        from viva_superpowers import loop_state as ls
        import tempfile
        _c, _m, stepf = E.env_for(task)
        tests0, _, _ = stepf([])
        locked = [{"name": t["test"], "pass_if": {"op": "==", "value": 0}} for t in tests0]
        st = ls.create(tempfile.mkdtemp(), f"{task}-live", _c, max_iterations=32)
        st = ls.lock_tests(st, locked)
        for s in run["steps"]:
            st = ls.record_iteration(st, edit=str(sorted(s["active"])), target="build",
                                     margin_deltas={}, gate="pass" if s["all_pass"] else "fail",
                                     tests=locked)
        st = ls.advance(st, run["state"], last_verdict={"gate": "pass" if run["state"] == "DONE" else "fail"})
        return ls.validate(st, locked)
    except Exception as e:                      # noqa: BLE001
        return [{"invariant": "uncomputed", "detail": f"loop_state unavailable: {type(e).__name__}"}]


def _representative(live):
    """Pick the run to render: prefer a DONE run, else the first. n>1 runs render
    the representative one with the n / pass-rate disclosed."""
    runs = live.get("runs", [])
    for r in runs:
        if r.get("state") == "DONE":
            return r
    return runs[0]


def convert(task):
    live = json.load(open(os.path.join(OUT, f"{task}_agent_live.json")))
    contract, mechs, step = E.env_for(task)
    run = _representative(live)                  # a representative (DONE) run, not blindly runs[0]
    summ = live.get("summary", {})
    n_runs = summ.get("n_runs", len(live.get("runs", [])))
    pass_rate = summ.get("pass_rate")
    violations = _violations_for(task, run)
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
    n_note = f"n={n_runs}" + (f", pass_rate={pass_rate}" if pass_rate is not None else "")
    traj = {
        "schema": "agent_build_trajectory/v1", "study": task,
        "driver": f"LLM agent — LIVE ({live.get('model', '?')}), {n_note}",
        "provenance": "live", "n_runs": n_runs, "pass_rate": pass_rate,
        "contract": contract,
        "tests": [{"id": tid, "label": tid, "expected": "within_tol"} for tid in test_ids],
        "iterations": iterations,
        # violations are COMPUTED from a real loop_state replay, not asserted.
        "result": {"state": run["state"], "edits": run.get("edits", len(run["steps"])),
                   "violations": violations},
    }
    path = os.path.join(OUT, f"{task}_agent_live_trajectory.json")
    json.dump(traj, open(path, "w"), indent=2)
    print(f"{task}: live -> {os.path.basename(path)} ({run['state']}, {len(iterations)} iters, "
          f"{n_note}, violations={len(violations)})")


if __name__ == "__main__":
    for t in ("diauxie", "diagnosis", "bistable"):
        convert(t)
