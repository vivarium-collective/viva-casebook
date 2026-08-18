"""Sandboxed runner for an agent-AUTHORED process-bigraph Process.

Reads {code, target, interval, duration} as JSON on stdin, execs the code to
define a Process subclass, validates it, wires it over a single store `X`, runs
the composite, and prints {ok, X_final, matched} JSON. Meant to be launched as a
SUBPROCESS with a timeout so untrusted generated code can't hang or wedge the
parent (Fable review #2 — the author-a-Process action).
"""
import json
import sys
import warnings

warnings.filterwarnings("ignore")


def _fail(msg):
    print(json.dumps({"ok": False, "error": msg}))
    sys.exit(0)


def main():
    req = json.loads(sys.stdin.read() or "{}")
    code = req.get("code", "")
    target = float(req.get("target", 5.0))
    dt = float(req.get("interval", 1.0))
    dur = float(req.get("duration", 30.0))

    from process_bigraph import Process, Composite, allocate_core

    ns = {"Process": Process}
    try:
        exec(code, ns)                       # untrusted generated code (subprocess-isolated)
    except Exception as e:                   # noqa: BLE001
        _fail(f"code failed to import: {type(e).__name__}: {e}")

    classes = [v for v in ns.values()
               if isinstance(v, type) and issubclass(v, Process) and v is not Process]
    if not classes:
        _fail("no process_bigraph Process subclass defined")
    cls = classes[-1]
    for m in ("config_schema", "inputs", "outputs", "update"):
        if not hasattr(cls, m):
            _fail(f"authored Process is missing `{m}`")

    core = allocate_core()
    core.register_link("Authored", cls)
    state = {"X": 0.0,
             "proc": {"_type": "process", "address": "local:Authored", "config": {},
                      "inputs": {"X": ["X"]}, "outputs": {"X": ["X"]}, "interval": dt}}
    try:
        comp = Composite({"state": state}, core=core)
        trace = []
        steps = max(1, int(round(dur / dt)))
        for _ in range(steps):
            comp.run(dt)
            trace.append(round(float(comp.state["X"]), 5))
        xf = trace[-1] if trace else 0.0
    except Exception as e:                   # noqa: BLE001
        _fail(f"run failed: {type(e).__name__}: {e}")

    tol = max(0.1, 0.05 * abs(target))
    print(json.dumps({"ok": True, "X_final": round(xf, 4), "target": target,
                      "matched": abs(xf - target) < tol, "trace": trace}))


if __name__ == "__main__":
    main()
