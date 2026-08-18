"""Task #5: choose a multicellular simulator, add subcellular models, hit a phenotype.

The contract wants a tissue-scale spatial differentiation GRADIENT. Getting it
requires two things a deterministic policy has no move for:
  1. SELECT the right multicellular simulator — a lattice engine with morphogen
     fields and cell-fate relabeling (CPM). Rigid-body (pymunk) and spatial-FBA
     have no cell-fate primitive; the phenotype is impossible on them.
  2. COMPOSE a subcellular fate model wired to the local field.

The policy's vocabulary is "install the mechanism a failing test names / step a
knob". There is no mechanism named for "multicellular" or "gradient", and
"choose a simulator" is not an install — so the policy has no move and GIVES UP.
The LLM agent reasons the simulator choice and the composition. Only the CPM
build runs a real composite (scripts/multicell_demo); the wrong-simulator builds
fail the phenotype honestly because the primitive isn't there.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import multicell_demo as M
from process_bigraph import Composite
from viva_superpowers import loop_state as ls, test_contract as tc

ROOT = M.__dict__.get("ROOT") or os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
OUT = os.path.join(ROOT, "workspace", "investigations", "model-building")

# simulator capabilities (what each multicellular engine provides)
SIMULATORS = {
    "cpm":     {"lattice": True,  "fields": True,  "cell_fate": True,  "desc": "Cellular Potts (viva-cpm): lattice + reaction-diffusion fields + per-cell fate relabeling"},
    "pymunk":  {"lattice": False, "fields": False, "cell_fate": False, "desc": "rigid-body physics (viva-munk): forces/collisions, no fields or cell-fate"},
    "spatial": {"lattice": True,  "fields": True,  "cell_fate": False, "desc": "spatial dFBA (spatio-flux): metabolic fields, but no cell-fate switch"},
}
COMPONENTS = {"wnt_field_niche", "stemness_fate_subcell"}

QUESTION = ("Produce a multicellular tissue with a spatial differentiation GRADIENT: cells near a "
            "signalling niche stay stem, and cells farther away differentiate — a tissue-scale "
            "phenotype, not a single-cell property.")

TESTS = ["simulator-fit", "multicellular", "differentiation-gradient"]


def grade_build(sim, components):
    """Grade a build = (chosen simulator, set of installed components). Returns
    {test: verdict}. The gradient is measured on a REAL run when CPM + both
    components are present; otherwise the required primitive is absent."""
    caps = SIMULATORS.get(sim, {"lattice": False, "fields": False, "cell_fate": False})
    fit = caps["lattice"] and caps["fields"] and caps["cell_fate"]
    verdicts = {"simulator-fit": "within_tol" if fit else "mismatch"}
    if sim == "cpm" and "wnt_field_niche" in components and "stemness_fate_subcell" in components:
        sim_obj = Composite({"state": M.build()}, core=M._vc_core.build_core())
        sim_obj.run(24)
        prog, achieved = M.phenotype(sim_obj)
        verdicts["multicellular"] = "within_tol" if len(prog) >= 4 else "mismatch"
        verdicts["differentiation-gradient"] = "within_tol" if achieved else "mismatch"
    else:
        # no real tissue phenotype without CPM + the composed subcell model
        verdicts["multicellular"] = "within_tol" if (sim in ("cpm", "spatial") and "wnt_field_niche" in components) else "mismatch"
        verdicts["differentiation-gradient"] = "mismatch"
    return verdicts


def env_step(sim, components):
    v = grade_build(sim, components)
    return {"simulator": sim, "components": sorted(components),
            "n_pass": sum(x == "within_tol" for x in v.values()), "n_hard": len(TESTS),
            "all_pass": all(x == "within_tol" for x in v.values()),
            "tests": [{"name": t, "verdict": v[t]} for t in TESTS]}


# ── deterministic policy: it can only install NAMED mechanisms; no simulator-select ──
NAIVE_MAP = {"multicellular": "wnt_field_niche"}   # the only test whose name suggests an install


def run_policy():
    sim, components = None, set()
    iterations, prev = [], {}
    st = ls.create(ROOT, "multicell-policy", QUESTION, max_iterations=8)
    st = ls.lock_tests(st, [{"name": t, "pass_if": {"op": ">=", "value": 1}} for t in TESTS])
    stall = 0
    for step in range(8):
        v = grade_build(sim or "pymunk", components)   # policy has no simulator preference → falls to a default
        n_pass = sum(x == "within_tol" for x in v.values())
        passing = {t: v[t] == "within_tol" for t in TESTS}
        newly = [] if step == 0 else [k for k in passing if passing[k] and not prev.get(k, False)]
        regressed = [k for k in passing if not passing[k] and prev.get(k, False)]
        fails = [t for t in TESTS if v[t] == "mismatch"]
        mech = next((NAIVE_MAP[t] for t in fails if t in NAIVE_MAP and NAIVE_MAP[t] not in components), None)
        if mech:
            decision = {"kind": "install", "mechanism": mech, "test": next(t for t in fails if NAIVE_MAP.get(t) == mech)}
        else:
            decision = {"kind": "blocked", "test": fails[0] if fails else None,
                        "note": "no mechanism is named for `simulator-fit`/`differentiation-gradient`, and 'choose a simulator' is not an install — the policy has no move"}
        tests_snap = [{"name": t, "verdict": v[t], "margin": None} for t in TESTS]
        if step > 0:
            st = ls.record_iteration(st, edit=(prevdec or {}).get("mechanism") or (prevdec or {}).get("note", "edit"),
                                     target="model", margin_deltas={}, gate="pass" if n_pass == len(TESTS) else "fail", tests=tests_snap)
        iterations.append({"iteration": step, "active": sorted(components) + ([sim] if sim else []),
                           "n_pass": n_pass, "n_hard": len(TESTS), "decision": decision,
                           "newly_fixed": newly, "regressed": regressed,
                           "tests": [{"id": t, "label": t, "verdict": v[t], "observed": v[t], "expected": "within_tol", "margin": None} for t in TESTS]})
        prev, prevdec = passing, decision
        if decision["kind"] == "install":
            components = set(components); components.add(decision["mechanism"]); stall = 0
        else:
            stall += 1
            if stall >= 2:
                st = ls.advance(st, "GIVE_UP", last_verdict={"gate": "fail", "reason": decision["note"]})
                return iterations, "GIVE_UP", st
        if n_pass == len(TESTS):
            st = ls.advance(st, "DONE", last_verdict={"gate": "pass"}); return iterations, "DONE", st
    st = ls.advance(st, "GIVE_UP", last_verdict={"gate": "fail", "reason": "budget exhausted"})
    return iterations, "GIVE_UP", st


def main():
    os.makedirs(OUT, exist_ok=True)
    iterations, outcome, st = run_policy()
    ls.save(ROOT, "multicell-policy", st)
    traj = {"schema": "model_build_trajectory/v2", "study": "multicell", "driver": "deterministic worst-margin policy",
            "contract": QUESTION, "tests": [{"id": t, "label": t, "expected": "within_tol"} for t in TESTS],
            "iterations": iterations, "result": {"state": outcome, "edits": len(iterations) - 1}}
    with open(os.path.join(OUT, "multicell_policy_trajectory.json"), "w") as fh:
        json.dump(traj, fh, indent=2)
    print("DETERMINISTIC POLICY on multicellular task:")
    for it in iterations:
        d = it["decision"]
        act = d["kind"] + (":" + d["mechanism"] if d["kind"] == "install" else "")
        print(f"  iter {it['iteration']} {it['n_pass']}/{it['n_hard']} {it['active']} -> {act}")
    print(f"RESULT: {outcome}")
    if outcome == "GIVE_UP":
        print(f"  stuck: {iterations[-1]['decision'].get('note','')}")


if __name__ == "__main__":
    main()
