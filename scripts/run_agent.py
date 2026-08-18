"""Live agentic model-building harness (Fable review #1b).

Drives a REAL LLM through the model-building environment (`agent_env`) via the
Anthropic Messages API with tool-use, and logs the verbatim transcript, model id,
and outcome — replacing the hardcoded `capture_*.py` DECISIONS arrays. The model
gets the contract + a `library_card` tool (functional mechanism descriptions +
citations, NO test→mechanism map) + a `step` tool returning graded verdicts, and
reasons turn-by-turn until all tests pass or it gives up.

Runs N independent trials (failures included) and writes, per task:
  workspace/investigations/model-building/<task>_agent_live.json
    { model, temperature, task, runs: [ {run_index, state, edits, transcript,
      steps: [{active, n_pass, n_hard, all_pass}] } ], summary: {...} }

Usage (needs ANTHROPIC_API_KEY in the env):
  python scripts/run_agent.py --task diauxie --runs 5 [--model claude-sonnet-4-5] [--budget 8]
  python scripts/run_agent.py --task all --runs 5
"""
import argparse
import json
import os
import sys
import warnings

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(__file__))
import agent_env as E  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
OUT = os.path.join(ROOT, "workspace", "investigations", "model-building")

SYSTEM = (
    "You are a model-building agent. Your job is to assemble a process-bigraph model — by "
    "installing a subset of the available mechanisms — that satisfies a set of LOCKED acceptance "
    "tests for an open modeling question. Work empirically: call `library_card` once to see the "
    "contract and the mechanisms (each has a FUNCTIONAL description and a citation — there is no "
    "hint about which test needs which mechanism), then call `step` with the mechanisms you choose "
    "to install and read the graded per-test verdicts and margins. Reason from the mechanism "
    "descriptions and the verdicts which mechanism a failing test needs; install the MINIMAL set. "
    "Iterate until every test reads within_tol. If you become convinced that no available mechanism "
    "can satisfy a still-failing test, stop and explain why you GIVE UP. Keep reasoning concise."
)

TOOLS = [
    {"name": "library_card", "description": "Return the contract + the installable mechanisms "
     "(functional description + citation each).", "input_schema": {"type": "object", "properties": {}}},
    {"name": "step", "description": "Install this exact set of mechanisms and grade the model. "
     "Returns per-test verdict/margin, n_pass/n_hard, all_pass.",
     "input_schema": {"type": "object",
                      "properties": {"active": {"type": "array", "items": {"type": "string"},
                                                "description": "mechanism names to install"}},
                      "required": ["active"]}},
]


def _run_once(client, model, temperature, task, budget):
    contract, mechs, step = E.env_for(task)
    card = {"contract": contract,
            "mechanisms": {m: {"description": d, "cite": c} for m, (d, c) in mechs.items()}}

    messages = [{"role": "user", "content":
                 f"Modeling task. Call library_card first.\n\nContract: {contract}"}]
    steps, transcript = [], []
    reached_done = False

    for _turn in range(budget):
        resp = client.messages.create(model=model, max_tokens=1600, system=SYSTEM,
                                      tools=TOOLS, temperature=temperature, messages=messages)
        text = "".join(b.text for b in resp.content if b.type == "text")
        tool_uses = [b for b in resp.content if b.type == "tool_use"]
        transcript.append({"role": "assistant", "text": text,
                           "tool_calls": [{"name": b.name, "input": b.input} for b in tool_uses]})
        messages.append({"role": "assistant", "content": resp.content})
        if not tool_uses:
            break  # model concluded (DONE or GIVE_UP) without another tool call
        results = []
        for b in tool_uses:
            if b.name == "library_card":
                payload = card
            else:
                active = (b.input or {}).get("active", [])
                unknown = [m for m in active if m not in mechs]
                if unknown:
                    payload = {"error": f"unknown mechanism(s): {unknown}", "available": sorted(mechs)}
                else:
                    tests, npass, nhard = step(active)
                    payload = {"active": sorted(active), "tests": tests, "n_pass": npass,
                               "n_hard": nhard, "all_pass": npass == nhard}
                    steps.append({"active": sorted(active), "n_pass": npass, "n_hard": nhard,
                                  "all_pass": npass == nhard})
                    reached_done = reached_done or (npass == nhard)
            results.append({"type": "tool_result", "tool_use_id": b.id,
                            "content": json.dumps(payload)})
        messages.append({"role": "user", "content": results})

    installs = {frozenset(s["active"]) for s in steps if s["active"]}
    return {"state": "DONE" if reached_done else "GIVE_UP",
            "edits": len(installs), "n_steps": len(steps), "steps": steps, "transcript": transcript}


def run_task(client, model, temperature, task, runs, budget):
    trials = [dict(_run_once(client, model, temperature, task, budget), run_index=i) for i in range(runs)]
    n_done = sum(t["state"] == "DONE" for t in trials)
    doc = {"schema": "agent_live_runs/v1", "task": task, "model": model, "temperature": temperature,
           "runs": trials,
           "summary": {"n_runs": runs, "n_done": n_done, "pass_rate": round(n_done / runs, 3),
                       "edits_when_done": sorted(t["edits"] for t in trials if t["state"] == "DONE")}}
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, f"{task}_agent_live.json")
    json.dump(doc, open(path, "w"), indent=2)
    print(f"{task}: {n_done}/{runs} DONE (model={model}) -> {os.path.relpath(path, ROOT)}")
    return doc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", default="diauxie", help="diauxie|diagnosis|bistable|all")
    ap.add_argument("--runs", type=int, default=5)
    ap.add_argument("--model", default="claude-sonnet-4-5")
    ap.add_argument("--temperature", type=float, default=1.0)
    ap.add_argument("--budget", type=int, default=8, help="max turns per run")
    a = ap.parse_args()
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("set ANTHROPIC_API_KEY to run the live harness")
    import anthropic
    client = anthropic.Anthropic()
    tasks = list(E.TASKS) if a.task == "all" else [a.task]
    for t in tasks:
        run_task(client, a.model, a.temperature, t, a.runs, a.budget)


if __name__ == "__main__":
    main()
