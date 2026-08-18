"""The model-building ENVIRONMENT for an actual LLM agent.

Given a model state (installed mechanisms + knob values), this builds the real
process-bigraph composite, runs it through the engine, and grades the locked
tests — returning the per-test verdicts + signed margins. It makes NO decisions:
an LLM agent reads the returned verdicts and decides the next edit (which
mechanism to install, which knob to calibrate), then calls this again. That
separation is what makes the loop genuinely agent-driven rather than scripted.

Usage:  echo '{"active": ["monod_uptake"], "knobs": {"qmax": 3.0, "Ks": 0.02}}' \\
          | python scripts/agent_step.py
Emits:  {"active", "knobs", "n_pass", "n_hard", "all_pass", "tests": [...]}
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import build_loop_demo as B   # reuse the real composite builder + tests + grading


def step(active, knobs):
    active = set(active or [])
    out = B.simulate(active, knobs or {})
    axes = B.grade(out)
    verd = {a["id"]: a for a in axes}
    hard = [t["id"] for t in B.TESTS if t["sev"] == "hard"]
    n_pass = sum(verd[h]["verdict"] == "within_tol" for h in hard)
    return {
        "active": sorted(active),
        "knobs": {k: round(float(v), 4) for k, v in (knobs or {}).items()},
        "n_pass": n_pass, "n_hard": len(hard), "all_pass": n_pass == len(hard),
        "tests": [{"id": a["id"], "label": B.BYID[a["id"]]["label"],
                   "verdict": a["verdict"], "observed": a["detail"]["observed"],
                   "expected": B.expected_str(B.BYID[a["id"]]),
                   "margin": (round(a["margin"], 4) if a.get("margin") is not None else None),
                   "severity": a.get("severity")} for a in axes],
    }


def library_card():
    """What the agent is allowed to install (invariant I3: provided mechanisms only)."""
    # NOTE: deliberately does NOT expose B.TEST_MECH (the test→mechanism map).
    # The agent gets a functional description of each mechanism + the contract,
    # and must reason which mechanism a failing test needs — leaking the map
    # would make the task multiple-choice with the answers printed on the card.
    return {"mechanisms": {m: {"knobs": v["knobs"], "cite": v["cite"]} for m, v in B.LIBRARY.items()},
            "contract": B.QUESTION}


if __name__ == "__main__":
    arg = sys.stdin.read().strip()
    req = json.loads(arg) if arg else {}
    if req.get("library"):
        print(json.dumps(library_card(), indent=2))
    else:
        print(json.dumps(step(req.get("active", []), req.get("knobs", {})), indent=2))
