"""Regenerate the AUTHOR-phase artifacts HONESTLY by running the real hardened
audit/lock/build machinery (Fable re-review, top-3 #3).

There is no LLM in this loop: it is a deterministic demonstration that exercises
`author_tests_task.py`'s real functions end-to-end and records exactly what they
return. It replaces the earlier `author_tests_live.json`, which claimed a
`final`-only test suite was "audit_sufficient" — the hardened audit (transient
nulls) now correctly rejects that suite, so the old artifact was false.

What it demonstrates, all real output:
  1. a PLAUSIBLE final-only band is flagged INSUFFICIENT (a spike-then-settle model
     passes it while blowing up mid-run — Fable's counterexample);
  2. a bounded suite (final band + max + min) passes the audit, locks with a
     re-verifiable hash, and a real first-order-relaxation Process builds + passes;
  3. the lock is ENFORCED — tampering the locked tests makes build() refuse.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import author_tests_task as AT  # noqa: E402

OUT = os.path.join(os.path.dirname(__file__), os.pardir, "workspace", "investigations", "model-building")
LOCK = AT._LOCK

# a real, cited first-order relaxation Process (the same idiom as the author task)
MODEL = (
    "class RelaxationToTargetProcess(Process):\n"
    "    # first-order relaxation to a set-point (proportional control; cf. linear ODE dX=k*(T-X))\n"
    "    config_schema = {'k': {'_type':'float','_default':0.6}, 'target': {'_type':'float','_default':5.0}}\n"
    "    def inputs(self): return {'X':'float'}\n"
    "    def outputs(self): return {'X':'float'}\n"
    "    def update(self, state, interval):\n"
    "        return {'X': self.config['k']*(self.config['target']-state['X'])*interval}\n"
)

NAIVE = [{"name": "final_low", "observable": "final", "op": ">=", "value": 4.5},
         {"name": "final_high", "observable": "final", "op": "<=", "value": 5.5}]
SUFFICIENT = NAIVE + [
    {"name": "no_blowup", "observable": "max", "op": "<=", "value": 5.5},
    {"name": "no_negative_excursion", "observable": "min", "op": ">=", "value": -0.5}]


def main():
    # start from a clean lock so the re-lock guard doesn't block regeneration
    if os.path.isfile(LOCK):
        os.remove(LOCK)

    naive_audit = AT.audit(NAIVE)                       # the plausible final-only suite -> insufficient
    suff_audit = AT.audit(SUFFICIENT)                   # bounded suite -> sufficient
    lock_res = AT.lock(SUFFICIENT)                      # audit-gated pre-registration
    build_res = AT.build(MODEL)                         # graded vs the LOCKED tests

    # demonstrate the lock is enforced: tamper the locked file, build must refuse
    doc = json.load(open(LOCK))
    doc["tests"] = doc["tests"] + [{"name": "sneaked_in", "observable": "final", "op": ">=", "value": 0.0}]
    json.dump(doc, open(LOCK, "w"), indent=2)
    tampered = AT.build(MODEL)
    # restore the honest lock
    AT.lock(SUFFICIENT, reopen=True)

    live = {
        "schema": "author_phase_demo/v1",
        "task": "author-phase (question -> AUTHOR tests -> hardened AUDIT -> LOCK -> BUILD)",
        "driver": "scripted deterministic demonstration of the audit/lock/build machinery — no LLM in "
                  "this loop; every verdict is real output of scripts/author_tests_task.py",
        "question": AT.QUESTION,
        "observables": AT.OBSERVABLES,
        "audit_catches_insufficiency_demo": {
            "naive_tests": NAIVE,
            "audit_sufficient": naive_audit["sufficient"],
            "degenerate_models_that_slip_through":
                [d["degenerate_model"] for d in naive_audit["degenerate_models_that_pass_your_tests"]],
            "note": "A `final`-only band looks reasonable, but a model that spikes to 1e6 mid-run and "
                    "settles to ~5 passes it while violating 'stays bounded'. The hardened audit RUNS "
                    "that transient null (spike_then_settle) and flags it — so the suite cannot lock.",
        },
        "full_cycle": {
            "authored_tests": SUFFICIENT,
            "audit_sufficient": suff_audit["sufficient"],
            "locked": lock_res.get("locked"),
            "tests_hash": lock_res.get("tests_hash"),
            "built_process": "RelaxationToTargetProcess — first-order relaxation dX=k*(target-X), cited",
            "build_all_pass": build_res.get("all_pass"),
            "n_pass": build_res.get("n_pass"), "n_hard": build_res.get("n_hard"),
            "observed": build_res.get("observables"),
            "reasoning": "A final-only band is insufficient (the audit shows spike/dip nulls slip through), "
                         "so the suite adds max<=5.5 (rejects transient blow-up) and min>=-0.5 (rejects a "
                         "negative excursion). That bounded suite passes the audit; locked; a first-order "
                         "relaxation Process then converges boundedly to 5 -> all tests pass.",
        },
        "lock_enforced_demo": {
            "tampered_locked_tests": True,
            "build_refused": (not tampered.get("ok", True)) and "LOCK INTEGRITY" in (tampered.get("error") or ""),
            "error": tampered.get("error"),
            "note": "build() recomputes the canonical hash of the locked tests and refuses to grade when "
                    "it no longer matches the pre-registered hash — the lock is enforced, not decorative.",
        },
        "summary": {
            "note": "The hardened audit now rejects the previously-'sufficient' final-only suite (Fable's "
                    "counterexample), forces bounded tests, and the pre-registration hash is enforced at "
                    "build time. Deterministic — reproduce with `python scripts/gen_author_tests_demo.py`.",
        },
    }
    path = os.path.join(OUT, "author_tests_live.json")
    json.dump(live, open(path, "w"), indent=2)
    print("naive final-only audit sufficient?  ", naive_audit["sufficient"],
          "(slip:", [d["degenerate_model"] for d in naive_audit["degenerate_models_that_pass_your_tests"]], ")")
    print("bounded suite audit sufficient?     ", suff_audit["sufficient"])
    print("locked?                              ", lock_res.get("locked"), lock_res.get("tests_hash", "")[:18])
    print("build all_pass?                      ", build_res.get("all_pass"), build_res.get("observables"))
    print("tamper -> build refused?             ", live["lock_enforced_demo"]["build_refused"])
    print("wrote", os.path.relpath(path))


if __name__ == "__main__":
    main()
