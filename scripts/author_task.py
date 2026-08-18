"""Author-a-Process task (Fable review #2): an OPEN action space.

The agent must WRITE a process-bigraph Process — there is deliberately NO library
mechanism for this, so no menu or enumeration can solve it; the agent has to
author code. The authored code runs SANDBOXED in a subprocess with a timeout.
Invariant I3 is reframed from "provided-mechanisms-only" (menu membership) to
"cited-mechanisms-only": the authored Process must carry a comment citing the
mechanism it implements. This is the "genuinely requires an agent" case.
"""
import json
import os
import re
import subprocess
import sys

TARGET = 5.0
INTERVAL, DURATION = 1.0, 30.0
RUNNER = os.path.join(os.path.dirname(__file__), "_author_runner.py")

CONTRACT = (
    f"Author a process-bigraph Process (Python) that drives the store `X` (which starts at 0) to a "
    f"steady value of {TARGET} and HOLDS it there for the rest of a short simulation. There is NO library "
    f"mechanism for this — you must write the Process yourself. Requirements: a class subclassing `Process` "
    f"(available in scope) with (1) a typed `config_schema` dict, (2) `inputs(self)` and `outputs(self)` "
    f"each returning {{'X': 'float'}}, and (3) `update(self, state, interval)` returning the per-step DELTA "
    f"to ADD to X (port apply is additive — you return a change, not the new value; `state['X']` is the "
    f"current value). The dynamics that bring X to the target and keep it there are yours to design. "
    f"Include a comment naming the mechanism or control law your update implements."
)

# I3 (Fable re-review): a citation must NAME a mechanism AND the code must MATCH that
# form — not just contain a keyword. `# feedback` alone no longer passes; a
# closed-loop law (feedback / relaxation / proportional / set-point) must actually
# read the current state, and an author-year reference is accepted on its own.
_NAMED_LAWS = {
    "hill": r"hill", "monod": r"monod", "michaelis": r"michaelis[- ]?menten|michaelis",
    "mass_action": r"mass[- ]?action", "logistic": r"logistic",
    "cooling": r"newton'?s? law of cooling|law of cooling|cooling",
    "feedback": r"\bfeedback\b", "proportional": r"proportional|\bP(ID|I|D)?\b control|proportional control",
    "relaxation": r"relaxation|exponential (approach|decay)|first[- ]?order",
    "setpoint": r"set[- ]?point|setpoint",
}
# laws that describe closed-loop / state-dependent dynamics: if cited, the update
# body MUST reference the current state (else the citation doesn't match the code).
_CLOSED_LOOP = {"cooling", "feedback", "proportional", "relaxation", "setpoint"}
_AUTHOR_YEAR = re.compile(r"#.*[A-Z][a-zA-Z]{2,}.*\b(1[89]\d\d|20\d\d)\b")
_COMMENT = re.compile(r"^\s*#.*$", re.M)
_READS_STATE = re.compile(r"state\s*(\[\s*['\"]X['\"]\s*\]|\.get\(\s*['\"]X['\"])")


def _cite_check(code):
    """(ok, error). Require a NAMED mechanism (or an author-year reference) in a
    comment, and if the named mechanism is a closed-loop law, require the code to
    actually read the state it claims to act on."""
    code = code or ""
    comments = "\n".join(_COMMENT.findall(code))
    if _AUTHOR_YEAR.search(code):                      # a real author-year reference stands on its own
        return True, None
    named = [k for k, pat in _NAMED_LAWS.items() if re.search(pat, comments, re.I)]
    if not named:
        return (False, "I3: the authored Process must include a comment NAMING the mechanism or control "
                "law it implements (e.g. a named law like 'first-order relaxation' / 'Hill', or an "
                "author-year reference) — a bare keyword is not a citation.")
    if set(named) & _CLOSED_LOOP and not _READS_STATE.search(code):
        return (False, "I3: you cite a closed-loop law (%s) but the update never reads the current "
                "`state['X']` — the citation must match the code's form (a feedback/relaxation law acts "
                "on the current value)." % ", ".join(sorted(set(named) & _CLOSED_LOOP)))
    return True, None


def author(code, timeout=15):
    ok, err = _cite_check(code)
    if not ok:
        return {"ok": False, "error": err}
    req = json.dumps({"code": code, "target": TARGET, "interval": INTERVAL, "duration": DURATION})
    try:
        p = subprocess.run([sys.executable, RUNNER], input=req, capture_output=True, text=True,
                           timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"authored code timed out (> {timeout}s) — possible infinite loop"}
    lines = (p.stdout or "").strip().splitlines()
    if lines:
        try:
            return json.loads(lines[-1])
        except Exception:                       # noqa: BLE001
            pass
    return {"ok": False, "error": ((p.stderr or p.stdout) or "no output")[-400:]}


if __name__ == "__main__":
    demo = (
        "class Producer(Process):\n"
        "    # first-order relaxation to a set-point (proportional control; cf. linear ODE dX=k(T-X))\n"
        "    config_schema = {'k': {'_type':'float','_default':0.6}, 'target': {'_type':'float','_default':5.0}}\n"
        "    def inputs(self): return {'X':'float'}\n"
        "    def outputs(self): return {'X':'float'}\n"
        "    def update(self, state, interval):\n"
        "        return {'X': self.config['k']*(self.config['target']-state['X'])*interval}\n"
    )
    print("known-good authored Process ->", author(demo))
    print("no-citation ->", author("class P(Process):\n    config_schema={}\n"))
    # closed-loop citation whose code ignores the state — must be rejected (form mismatch)
    open_loop = ("class P(Process):\n    # feedback\n    config_schema={}\n"
                 "    def inputs(self): return {'X':'float'}\n"
                 "    def outputs(self): return {'X':'float'}\n"
                 "    def update(self, state, interval): return {'X': 0.2}\n")
    print("cite=feedback but open-loop ->", author(open_loop))
