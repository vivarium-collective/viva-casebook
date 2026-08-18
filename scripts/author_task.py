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
    f"steady value of {TARGET} by the end of a short simulation. There is NO library mechanism for this — "
    f"you must write the Process yourself. Requirements: a class subclassing `Process` (available in "
    f"scope) with (1) a typed `config_schema` dict, (2) `inputs(self)` and `outputs(self)` each returning "
    f"{{'X': 'float'}}, and (3) `update(self, state, interval)` returning the per-step DELTA for X. Note: "
    f"port apply is ADDITIVE, so to converge to a target use e.g. dX = k*(target - state['X'])*interval. "
    f"Include a comment citing the mechanism/law you implement."
)

# I3 reframe: require a citation in the authored code (a reference, a named law, or a year)
_CITE = re.compile(r"#.*(cite|ref\b|references?|\b1[89]\d\d\b|\b20\d\d\b|et al|Hill|Monod|Michaelis|"
                   r"proportional|first-?order|relaxation|set[- ]?point|feedback)", re.I)


def author(code, timeout=15):
    if not _CITE.search(code or ""):
        return {"ok": False, "error": "I3: the authored Process must include a comment citing the "
                "mechanism/law it implements (a reference or named law), not just code."}
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
