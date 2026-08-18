"""AUTHOR-phase task (Fable review #4): the agent authors its OWN acceptance
tests, an audit catches a real insufficiency, then lock → build.

The loop's real novelty, demonstrated nowhere before: from an open question the
agent must WRITE sufficient acceptance tests, get them AUDITED, LOCK (pre-register)
them, then BUILD a model that passes them.

The audit is HARDENED (Fable #5): instead of trusting a `classification` label or
an LLM promise, it RUNS a set of DEGENERATE null models and checks that the
authored tests actually REJECT them. Tests are sufficient only when no degenerate
behaviour slips through — an executable sufficiency check.
"""
import json
import os
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))

QUESTION = ("Build a model where the store `X` (starting at 0) converges to a target value near 5 and "
            "stays BOUNDED — it must not collapse to 0, blow up without bound, or settle at the wrong "
            "value. First AUTHOR acceptance tests that capture this, get them audited, lock them, then "
            "build a Process that passes them.")
OBSERVABLES = ["final", "max", "min", "mean"]
_RUNNER = os.path.join(os.path.dirname(__file__), "_author_runner.py")
_LOCK = os.path.join(os.path.dirname(__file__), os.pardir, "workspace", "investigations",
                     "model-building", "author_tests_lock.json")

# degenerate behaviours the tests MUST reject (the executable audit controls)
_NULLS = {
    "collapse_to_zero": [0.0] * 30,
    "blow_up":          [1.6 ** i for i in range(30)],
    "wrong_target_100": [100.0 * (1 - 0.85 ** (i + 1)) for i in range(30)],
}


def observables(trace):
    a = np.array(trace, dtype=float) if trace else np.array([0.0])
    return {"final": round(float(a[-1]), 4), "max": round(float(a.max()), 4),
            "min": round(float(a.min()), 4), "mean": round(float(a.mean()), 4)}


def _check(t, obs):
    v = obs.get(t.get("observable"))
    if v is None:
        return False
    op, val = t.get("op"), float(t.get("value", 0))
    return (v >= val) if op == ">=" else (v <= val) if op == "<=" else False


def _passes_all(tests, trace):
    obs = observables(trace)
    return all(_check(t, obs) for t in tests), obs


def _valid(tests):
    return [t for t in (tests or []) if isinstance(t, dict) and t.get("observable") in OBSERVABLES
            and t.get("op") in (">=", "<=") and "value" in t]


def audit(tests):
    tests = _valid(tests)
    if not tests:
        return {"sufficient": False, "reason": "no valid tests authored "
                "(each test = {name, observable in %s, op '>='|'<=', value})" % OBSERVABLES}
    slip = []
    for name, tr in _NULLS.items():
        ok, obs = _passes_all(tests, tr)
        if ok:
            slip.append({"degenerate_model": name, "observables": obs})
    suff = not slip
    return {"sufficient": suff, "n_tests": len(tests),
            "degenerate_models_that_pass_your_tests": slip,
            "note": ("No degenerate model passes — the tests discriminate the intended behaviour."
                     if suff else
                     "These degenerate models pass ALL your tests, so the tests do not exclude them. "
                     "Add a test that each one fails.")}


def lock(tests):
    a = audit(tests)
    if not a["sufficient"]:
        return {"locked": False, "audit": a,
                "error": "AUDIT gate: tests are not sufficient — revise so no degenerate model passes."}
    tests = _valid(tests)
    try:
        import tempfile
        from viva_superpowers import loop_state as ls
        st = ls.create(tempfile.mkdtemp(), "author-tests", QUESTION)
        st = ls.lock_tests(st, [{"name": t.get("name", t["observable"]),
                                 "pass_if": {"op": t["op"], "value": t["value"]}} for t in tests])
        thash = st.get("locked_tests_hash")
    except Exception:                          # noqa: BLE001
        thash = None
    os.makedirs(os.path.dirname(_LOCK), exist_ok=True)
    json.dump({"tests": tests, "tests_hash": thash}, open(_LOCK, "w"), indent=2)
    return {"locked": True, "n_tests": len(tests), "tests_hash": thash,
            "note": "Tests pre-registered. Now build a model that passes them; the locked tests cannot change."}


def _run_model(code):
    req = json.dumps({"code": code, "target": 5.0, "interval": 1.0, "duration": 30.0})
    try:
        p = subprocess.run([sys.executable, _RUNNER], input=req, capture_output=True, text=True, timeout=15)
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "authored code timed out"}
    lines = (p.stdout or "").strip().splitlines()
    if lines:
        try:
            return json.loads(lines[-1])
        except Exception:                      # noqa: BLE001
            pass
    return {"ok": False, "error": ((p.stderr or p.stdout) or "no output")[-400:]}


def build(code):
    if not os.path.isfile(_LOCK):
        return {"error": "lock the tests first: audit → lock → build"}
    locked = json.load(open(_LOCK))["tests"]
    res = _run_model(code)
    if not res.get("ok"):
        return {"ok": False, "error": res.get("error")}
    obs = observables(res.get("trace") or [])
    verdicts = [{"name": t.get("name", t["observable"]), "observable": t["observable"], "op": t["op"],
                 "value": t["value"], "observed": obs[t["observable"]], "pass": _check(t, obs)}
                for t in locked]
    npass = sum(v["pass"] for v in verdicts)
    return {"ok": True, "observables": obs, "tests": verdicts, "n_pass": npass,
            "n_hard": len(locked), "all_pass": npass == len(locked)}
