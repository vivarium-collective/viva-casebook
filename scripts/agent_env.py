"""The model-building ENVIRONMENT as a CLI (the agent's two tools).

Presents a task to a model-building agent and grades its builds — with NO leak of
the test→mechanism answer key (Fable review). The agent sees:
  - the contract (the open modeling question + the locked acceptance tests),
  - a `card` of mechanisms with a FUNCTIONAL description + citation each,
  - and, on each `step`, the graded per-test verdicts/margins for a chosen set of
    installed mechanisms.
It must REASON which mechanisms a failing test needs.

Usage (JSON on argv or stdin):
  python scripts/agent_env.py <task> card
  python scripts/agent_env.py <task> step '{"active": ["glucose_uptake", ...]}'

<task> ∈ {diauxie, diagnosis, bistable}. Deterministic; every verdict is real
process-bigraph engine output.
"""
import json
import os
import sys
import warnings

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(__file__))


# --- task adapters: contract + FUNCTIONAL mechanism descriptions + a step() grader ---
def _diauxie():
    import diauxie_demo as D
    mechs = {
        "glucose_uptake": ("A Monod uptake process: consumes glucose and converts it to biomass.",
                           "Monod 1949 (growth kinetics)"),
        "lactose_uptake": ("A Monod uptake process for lactose → biomass; its rate is gated by a "
                           "`lac_repression` store (1 = fully active).", "Monod 1949"),
        "catabolite_repression": ("A Hill switch that writes the `lac_repression` store from the current "
                                  "glucose level (high glucose → low value).", "Jacob & Monod 1961"),
    }

    def step(active):
        axes = D.grade(D.simulate(set(active), {}))
        tests = [{"test": a["id"], "verdict": a["verdict"], "observed": a["detail"]["observed"],
                  "expected": D.exp_str(a["id"]), "margin": a.get("margin")} for a in axes]
        npass = sum(a["verdict"] == "within_tol" for a in axes)
        return tests, npass, len(D.TESTS)
    return D.QUESTION, mechs, step


def _diagnosis():
    import diagnosis_task as T
    mechs = {
        "boost_uptake": ("Raises the cell's maximum nutrient uptake rate (qmax).", "Monod 1949"),
        "boost_yield": ("Raises the biomass yield per unit nutrient consumed.", "Pirt 1965"),
        "stabilize_membrane": ("Removes the membrane stressor so viability no longer decays.",
                               "membrane-integrity / viability"),
    }

    def step(active):
        v, margins, o = T.grade(set(active))
        obs = {"biomass": round(o["biomass"], 3), "nutrient_final": round(o["nutrient"], 3),
               "viability_final": round(o["viability"], 3)}
        tests = [{"test": t, "verdict": v[t], "margin": round(margins[t], 3), "observables": obs}
                 for t in T.TESTS]
        npass = sum(x == "within_tol" for x in v.values())
        return tests, npass, len(T.TESTS)
    return T.QUESTION, mechs, step


def _bistable():
    import bistable_task as T
    mechs = {
        "boost_expression": ("Raises the expression rate (beta) of both genes.", "gene expression"),
        "add_degradation": ("Raises the degradation rate of both gene products.", "protein turnover"),
        "cooperative_binding": ("Makes the mutual repression cooperative (Hill exponent n≥2 instead of 1).",
                                "Gardner et al. 2000 (toggle switch)"),
    }

    def step(active):
        v, margins, o = T.grade(set(active))
        tests = [{"test": t, "verdict": v[t], "margin": round(margins[t], 3),
                  "state_separation": round(o["sep"], 3)} for t in T.TESTS]
        npass = sum(x == "within_tol" for x in v.values())
        return tests, npass, len(T.TESTS)
    return T.QUESTION, mechs, step


TASKS = {"diauxie": _diauxie, "diagnosis": _diagnosis, "bistable": _bistable}


def env_for(task):
    if task not in TASKS:
        raise SystemExit(f"unknown task {task!r}; choose from {sorted(TASKS)}")
    return TASKS[task]()


def main():
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    task, cmd = sys.argv[1], sys.argv[2]

    # data-grounded BioModels break-and-repair task: different action shape
    # (repair a parameter) and observation (the divergence from the reference model)
    if task == "repair":
        import biomodels_repair_task as R
        if cmd == "card":
            bs = R.broken_state()
            out = {"contract": "A curated BioModels model (Elowitz 2000 repressilator) no longer "
                   "reproduces its REFERENCE time-course because one kinetic parameter was changed. "
                   "Diagnose which parameter is wrong and repair it — set it to a value that restores "
                   "the reference behaviour (rmsd_vs_reference below tolerance). The reference model is "
                   "the ground truth; there is no author-set band.",
                   "parameters": bs["parameters"], "rmsd_vs_reference": bs["rmsd_vs_reference"],
                   "how": "Call `step` with {\"param\": name, \"value\": number} to set a parameter and "
                          "see the new rmsd_vs_reference (matched=true when it drops below tolerance)."}
        elif cmd == "step":
            arg = sys.argv[3] if len(sys.argv) > 3 else sys.stdin.read()
            req = json.loads(arg) if arg.strip() else {}
            out = R.repair(req.get("param"), req.get("value"))
        else:
            raise SystemExit("use 'card' or 'step'")
        print(json.dumps(out, indent=2))
        return

    contract, mechs, step = env_for(task)
    if cmd == "card":
        out = {"contract": contract,
               "mechanisms": {m: {"description": d, "cite": c} for m, (d, c) in mechs.items()},
               "how": "Install a subset of mechanisms with `step`; read the graded verdicts; iterate."}
    elif cmd == "step":
        arg = sys.argv[3] if len(sys.argv) > 3 else sys.stdin.read()
        req = json.loads(arg) if arg.strip() else {}
        active = req.get("active", [])
        unknown = [m for m in active if m not in mechs]
        if unknown:
            out = {"error": f"unknown mechanism(s): {unknown}", "available": sorted(mechs)}
        else:
            tests, npass, nhard = step(active)
            out = {"active": sorted(active), "tests": tests, "n_pass": npass, "n_hard": nhard,
                   "all_pass": npass == nhard}
    else:
        raise SystemExit(f"unknown cmd {cmd!r}; use 'card' or 'step'")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
