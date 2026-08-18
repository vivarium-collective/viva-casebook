"""Render ALL seven agent-vs-policy pages from their committed trajectories with
the CORRECT per-task insight and honest provenance (Fable re-review, top-3 #1).

Fixes the class of bug where one task's insight (the diauxie lactose story) was
pasted onto five other pages, and where live pages misstated their provenance.
Each page is rendered from its own trajectory:
  - diauxie / diagnosis / bistable  -> the LIVE trajectories (n disclosed, violations
    computed from a real loop_state replay), each with its own correct insight;
  - bounded-cell / multicell / multiscale / sbml -> illustrative hand-authored
    transcripts, each with its own accurate (task-specific) insight and an
    "illustrative, not live" provenance banner.

Run:  PYTHONPATH=<repo> python scripts/render_all_pages.py
"""
import os
import subprocess
import sys

HERE = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(HERE, os.pardir))
INV = os.path.join(ROOT, "workspace", "investigations", "model-building")
DOCS = os.path.join(ROOT, "docs")

# name, agent_traj, policy_traj, out.html, insight-key, title
PAGES = [
    ("bounded-cell", "agent_trajectory.json", "trajectory.json",
     "agent-vs-policy.html", "calibration", "LLM agent vs deterministic policy — bounded cell"),
    ("diauxie", "diauxie_agent_live_trajectory.json", "diauxie_policy_trajectory.json",
     "diauxie-agent-vs-policy.html", "giveup", "Diauxic growth — LLM agent vs deterministic policy"),
    ("diagnosis", "diagnosis_agent_live_trajectory.json", "diagnosis_policy_trajectory.json",
     "diagnosis-agent-vs-policy.html", "diagnosis", "Ambiguous diagnosis — LLM agent vs deterministic policy"),
    ("bistable", "bistable_agent_live_trajectory.json", "bistable_policy_trajectory.json",
     "bistable-agent-vs-policy.html", "bistable", "Bistable genetic switch — LLM agent vs deterministic policy"),
    ("multicell", "multicell_agent_trajectory.json", "multicell_policy_trajectory.json",
     "multicell-agent-vs-policy.html", "multicell", "Multicellular differentiation — agent vs policy"),
    ("multiscale", "multiscale_agent_trajectory.json", "multiscale_policy_trajectory.json",
     "multiscale-agent-vs-policy.html", "multiscale", "Multiscale coupling — agent vs policy"),
    ("sbml", "sbml_agent_trajectory.json", "sbml_policy_trajectory.json",
     "sbml-agent-vs-policy.html", "sbml", "SBML pathway build — agent vs policy"),
]


def main():
    rc = os.path.join(HERE, "render_comparison.py")
    for name, agent, policy, out, insight, title in PAGES:
        cmd = [sys.executable, rc,
               "--agent", os.path.join(INV, agent),
               "--policy", os.path.join(INV, policy),
               "--out", os.path.join(DOCS, out),
               "--insight", insight, "--title", title]
        p = subprocess.run(cmd, capture_output=True, text=True)
        tag = "ok " if p.returncode == 0 else "FAIL"
        print(f"[{tag}] {name:12s} {out:32s} {(p.stdout or p.stderr).strip().splitlines()[-1] if (p.stdout or p.stderr).strip() else ''}")
        if p.returncode != 0:
            print(p.stderr)


if __name__ == "__main__":
    main()
