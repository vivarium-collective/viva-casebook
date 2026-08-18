"""Task #7: build an SBML model, load it into viva-copasi/COPASI, test its quality.

The agent must author a KINETIC SBML model of a linear metabolic pathway (A→B→C)
that COPASI can load and simulate to a valid steady state, with mass conserved and
the terminal product C accumulating. The 'model' is real SBML (libsbml), loaded
into the real COPASI backend (basico, via viva-copasi) and graded by simulation.

Building a correct reaction network — the right reactions with balanced
stoichiometry and kinetics so the pathway flows and mass conserves — is not a
knob or a mechanism a failing test names. The deterministic policy has no move to
author SBML structure and GIVES UP; the LLM reasons the pathway and builds it.
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(__file__))
import libsbml
import basico
from viva_superpowers import loop_state as ls

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
OUT = os.path.join(ROOT, "workspace", "investigations", "model-building")

# available reactions the agent can add to build the pathway
REACTIONS = {
    "A->B": ("A", "B", 0.6),
    "B->C": ("B", "C", 0.4),
}
SPECIES0 = {"A": 10.0, "B": 0.0, "C": 0.0}
QUESTION = ("Build an SBML kinetic model of a linear metabolic pathway A→B→C that COPASI can load and "
            "simulate to a valid steady state, with total mass conserved and the terminal product C "
            "accumulating as the dominant species.")
TESTS = ["sbml-valid", "copasi-loads", "steady-state", "mass-conserved", "terminal-product"]


def build_sbml(active_reactions):
    d = libsbml.SBMLDocument(3, 2)
    m = d.createModel(); m.setId("pathway")
    c = m.createCompartment(); c.setId("cell"); c.setConstant(True); c.setSize(1.0); c.setSpatialDimensions(3)
    used = set()
    for rk in active_reactions:
        a, b, _ = REACTIONS[rk]; used.add(a); used.add(b)
    for sid, amt in SPECIES0.items():
        if sid in used or sid == "A":
            s = m.createSpecies(); s.setId(sid); s.setCompartment("cell")
            s.setInitialConcentration(amt); s.setConstant(False)
            s.setBoundaryCondition(False); s.setHasOnlySubstanceUnits(False)
    for rk in active_reactions:
        a, b, k = REACTIONS[rk]
        r = m.createReaction(); r.setId(rk.replace("->", "_to_")); r.setReversible(False); r.setFast(False)
        sr = r.createReactant(); sr.setSpecies(a); sr.setConstant(True); sr.setStoichiometry(1)
        pr = r.createProduct(); pr.setSpecies(b); pr.setConstant(True); pr.setStoichiometry(1)
        kl = r.createKineticLaw(); lp = kl.createLocalParameter(); lp.setId("k"); lp.setValue(k)
        kl.setMath(libsbml.parseL3Formula(f"k * {a}"))
    return d


def grade(active_reactions):
    v = {t: "mismatch" for t in TESTS}
    if not active_reactions:
        return v
    d = build_sbml(active_reactions)
    d.checkConsistency()
    fatal = sum(1 for i in range(d.getNumErrors())
                if d.getError(i).getSeverity() >= libsbml.LIBSBML_SEV_ERROR)
    v["sbml-valid"] = "within_tol" if fatal == 0 else "mismatch"
    sbml = libsbml.writeSBMLToString(d)
    f = tempfile.NamedTemporaryFile(suffix=".xml", delete=False)
    f.write(sbml.encode()); f.close()
    try:
        basico.load_model(f.name)
        v["copasi-loads"] = "within_tol"
        tc = basico.run_time_course(duration=40, intervals=40)
        totals = tc[[s for s in ("A", "B", "C") if s in tc.columns]].sum(axis=1)
        v["mass-conserved"] = "within_tol" if abs(float(totals.iloc[-1]) - float(totals.iloc[0])) < 0.2 else "mismatch"
        try:
            basico.run_steadystate(); v["steady-state"] = "within_tol"
        except Exception:
            v["steady-state"] = "mismatch"
        finals = {s: float(tc[s].iloc[-1]) for s in ("A", "B", "C") if s in tc.columns}
        cval = finals.get("C", 0.0)
        v["terminal-product"] = "within_tol" if (cval >= 8.0 and cval == max(finals.values())) else "mismatch"
    except Exception:
        pass
    finally:
        os.unlink(f.name)
    return v


def env_step(active):
    v = grade(active)
    return {"active": sorted(active), "n_pass": sum(x == "within_tol" for x in v.values()),
            "n_hard": len(TESTS), "all_pass": all(x == "within_tol" for x in v.values()),
            "tests": [{"name": t, "verdict": v[t]} for t in TESTS]}


NAIVE_MAP = {}   # no reaction is 'named' by any failing test — the policy can't author SBML structure


def run_policy():
    active = set()
    iterations, prev = [], {}
    st = ls.create(ROOT, "sbml-policy", QUESTION, max_iterations=8)
    st = ls.lock_tests(st, [{"name": t, "pass_if": {"op": ">=", "value": 1}} for t in TESTS])
    stall = 0
    for step in range(6):
        v = grade(active)
        n_pass = sum(x == "within_tol" for x in v.values())
        passing = {t: v[t] == "within_tol" for t in TESTS}
        newly = [] if step == 0 else [k for k in passing if passing[k] and not prev.get(k, False)]
        decision = {"kind": "blocked", "test": next((t for t in TESTS if v[t] == "mismatch"), None),
                    "note": "no reaction is named by any failing test, and 'author an SBML reaction network "
                            "with balanced stoichiometry + kinetics' is not an install — the policy has no move"}
        tests_snap = [{"name": t, "verdict": v[t], "margin": None} for t in TESTS]
        if step > 0:
            st = ls.record_iteration(st, edit=(prevdec or {}).get("note", "edit"), target="model",
                                     margin_deltas={}, gate="fail", tests=tests_snap)
        iterations.append({"iteration": step, "active": sorted(active), "n_pass": n_pass, "n_hard": len(TESTS),
                           "decision": decision, "newly_fixed": newly, "regressed": [],
                           "tests": [{"id": t, "label": t, "verdict": v[t], "observed": v[t], "expected": "within_tol", "margin": None} for t in TESTS]})
        prev, prevdec = passing, decision
        stall += 1
        if stall >= 2:
            st = ls.advance(st, "GIVE_UP", last_verdict={"gate": "fail", "reason": decision["note"]})
            return iterations, "GIVE_UP", st
    st = ls.advance(st, "GIVE_UP", last_verdict={"gate": "fail", "reason": "budget exhausted"})
    return iterations, "GIVE_UP", st


def main():
    os.makedirs(OUT, exist_ok=True)
    iterations, outcome, st = run_policy()
    ls.save(ROOT, "sbml-policy", st)
    traj = {"schema": "model_build_trajectory/v2", "study": "sbml", "driver": "deterministic worst-margin policy",
            "contract": QUESTION, "tests": [{"id": t, "label": t, "expected": "within_tol"} for t in TESTS],
            "iterations": iterations, "result": {"state": outcome, "edits": len(iterations) - 1}}
    with open(os.path.join(OUT, "sbml_policy_trajectory.json"), "w") as fh:
        json.dump(traj, fh, indent=2)
    print("DETERMINISTIC POLICY on SBML/COPASI task:")
    for it in iterations:
        print(f"  iter {it['iteration']} {it['n_pass']}/{it['n_hard']} {it['active']} -> {it['decision']['kind']}")
    print(f"RESULT: {outcome}")


if __name__ == "__main__":
    main()
