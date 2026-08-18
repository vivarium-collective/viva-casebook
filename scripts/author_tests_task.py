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
import hashlib
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

# degenerate behaviours the tests MUST reject (the executable audit controls).
# The endpoint-in-band TRANSIENT nulls (spike_then_settle, dip_then_settle) are the
# ones Fable's re-review exposed: they end near 5 — so `final`-only tests pass them —
# yet the trajectory blows up or goes negative mid-run, violating "stays bounded".
# Rejecting them forces the author to bound `max` and `min`, not just `final`.
_SETTLE = [round(5.0 * (1 - 0.7 ** (i + 1)), 4) for i in range(30)]   # smooth 0->5 (like a real relaxation)
_SPIKE = _SETTLE[:]; _SPIKE[18], _SPIKE[19] = 1e6, 5e4               # transient blow-up, settles to ~5
_DIP = _SETTLE[:]; _DIP[18], _DIP[19] = -1e3, -50.0                  # transient negative excursion, settles to ~5
_NULLS = {
    "collapse_to_zero":  [0.0] * 30,
    "blow_up":           [1.6 ** i for i in range(30)],
    "wrong_target_100":  [100.0 * (1 - 0.85 ** (i + 1)) for i in range(30)],
    "spike_then_settle": _SPIKE,
    "dip_then_settle":   _DIP,
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


def _canonical_hash(tests):
    """A self-contained sha256 over the normalized tests, so build() can verify the
    lock without a persisted loop_state dir. Order-independent."""
    norm = sorted(({"observable": t["observable"], "op": t["op"], "value": float(t["value"])}
                   for t in _valid(tests)), key=lambda t: (t["observable"], t["op"], t["value"]))
    return hashlib.sha256(json.dumps(norm, sort_keys=True).encode()).hexdigest()


def lock(tests, reopen=False):
    a = audit(tests)
    if not a["sufficient"]:
        return {"locked": False, "audit": a,
                "error": "AUDIT gate: tests are not sufficient — revise so no degenerate model passes."}
    tests = _valid(tests)
    thash = _canonical_hash(tests)
    reopened_from = []
    # re-lock guard: refuse to silently replace a DIFFERENT existing lock unless
    # reopen=True, and then record the supplanted hash as a reopen trail.
    if os.path.isfile(_LOCK):
        prev = json.load(open(_LOCK))
        if prev.get("tests_hash") and prev["tests_hash"] != thash and not reopen:
            return {"locked": False, "error": "a DIFFERENT set of tests is already locked "
                    f"({prev['tests_hash'][:12]}…). Pre-registration is immutable; pass reopen=true to "
                    "replace it — the supplanted lock is recorded as a reopen trail.",
                    "existing_hash": prev["tests_hash"], "attempted_hash": thash}
        reopened_from = prev.get("reopened_from", [])
        if prev.get("tests_hash") and prev["tests_hash"] != thash:
            reopened_from = reopened_from + [prev["tests_hash"]]
    # cross-check with the I1-I5 loop_state machinery when available (advisory)
    try:
        import tempfile
        from viva_superpowers import loop_state as ls
        st = ls.create(tempfile.mkdtemp(), "author-tests", QUESTION)
        st = ls.lock_tests(st, [{"name": t.get("name", t["observable"]),
                                 "pass_if": {"op": t["op"], "value": t["value"]}} for t in tests])
        ls_hash = st.get("locked_tests_hash")
    except Exception:                          # noqa: BLE001
        ls_hash = None
    os.makedirs(os.path.dirname(_LOCK), exist_ok=True)
    json.dump({"tests": tests, "tests_hash": thash, "loop_state_hash": ls_hash,
               "reopened_from": reopened_from}, open(_LOCK, "w"), indent=2)
    return {"locked": True, "n_tests": len(tests), "tests_hash": thash, "reopened_from": reopened_from,
            "note": "Tests pre-registered. Now build a model that passes them; the locked tests cannot "
                    "change (build() re-verifies this hash)."}


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
    lock_doc = json.load(open(_LOCK))
    locked = lock_doc["tests"]
    # ENFORCE pre-registration: the locked tests must hash to the recorded value.
    # Editing the lock file (or the tests) between lock and build is refused here.
    recomputed = _canonical_hash(locked)
    if lock_doc.get("tests_hash") and recomputed != lock_doc["tests_hash"]:
        return {"ok": False, "error": "LOCK INTEGRITY: the locked tests no longer match their "
                f"pre-registration hash (recorded {lock_doc['tests_hash'][:12]}…, got {recomputed[:12]}…). "
                "The lock was tampered with after pre-registration — refusing to grade."}
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
