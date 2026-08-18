"""Diauxie: a modeling task that a deterministic policy CANNOT solve.

Same loop, real process-bigraph composite, same environment/grading as
build_loop_demo.py — but the contract asks for the diauxic phenotype (glucose
consumed FIRST, then lactose, sequentially). The catch: fixing the ordering
failure is not a knob and not a mechanism the failing test names — it needs a
regulatory COUPLING (catabolite repression gating lactose uptake by glucose).

This module runs the DETERMINISTIC worst-negative-margin policy, whose action
vocabulary is "install the mechanism the failing test maps to, or calibrate a
knob". Its map (authored from the test names, as an engineer would) has entries
for the consumption/growth tests but NONE for `diauxic-order` — because no
mechanism is *named* for it. So the policy installs both uptakes, gets the
regulation wrong, and GIVES UP honestly. The LLM agent (scripts/agent_step.py +
a live run) reaches for repression by reasoning about the biology.
"""
import json
import os
import sys

import numpy as np
from process_bigraph import Composite

sys.path.insert(0, os.path.dirname(__file__))
import viva_casebook.core as _vc_core
from viva_superpowers import loop_state as ls, test_contract as tc

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
OUT = os.path.join(ROOT, "workspace", "investigations", "model-building")
T_END, DT = 12.0, 0.02
_CORE = None


def _core():
    global _CORE
    if _CORE is None:
        _CORE = _vc_core.build_core()
    return _CORE


LIBRARY = {
    "glucose_uptake":       {"knobs": {"Vg": 2.0, "Kg": 0.5, "Y": 0.45}, "cite": "Monod 1949 (glucose uptake)"},
    "lactose_uptake":       {"knobs": {"Vl": 2.0, "Kl": 0.5, "Y": 0.45}, "cite": "Monod 1949 (lactose uptake)"},
    "catabolite_repression": {"knobs": {"Ki": 0.5, "n": 4.0}, "cite": "Monod 1942 diauxie; Jacob & Monod 1961 (lac repression)"},
}
# The deterministic policy's authored map: from a FAILING test to the mechanism
# to install. Note: NO entry for diauxic-order — no mechanism is named for it.
NAIVE_MAP = {"glucose-consumed": "glucose_uptake", "lactose-consumed": "lactose_uptake",
             "growth": "lactose_uptake"}


def _node(a, cfg, i, o):
    return {"_type": "process", "address": "local:" + a, "config": cfg, "inputs": i, "outputs": o, "interval": DT}


def simulate(active, knobs):
    core = _core()
    st = {"glucose": 10.0, "lactose": 10.0, "biomass": 0.5, "lac_repression": 1.0,
          "glu_flux": 0.0, "lac_flux": 0.0}
    if "glucose_uptake" in active:
        st["gu"] = _node("GlucoseUptake", {k: knobs.get(k, LIBRARY["glucose_uptake"]["knobs"][k]) for k in ("Vg", "Kg", "Y")},
                        {"glucose": ["glucose"], "biomass": ["biomass"]},
                        {"glucose": ["glucose"], "biomass": ["biomass"], "glu_flux": ["glu_flux"]})
    if "lactose_uptake" in active:
        st["lu"] = _node("LactoseUptake", {k: knobs.get(k, LIBRARY["lactose_uptake"]["knobs"][k]) for k in ("Vl", "Kl", "Y")},
                        {"lactose": ["lactose"], "biomass": ["biomass"], "lac_repression": ["lac_repression"]},
                        {"lactose": ["lactose"], "biomass": ["biomass"], "lac_flux": ["lac_flux"]})
    if "catabolite_repression" in active:
        st["cr"] = _node("CataboliteRepression", {k: knobs.get(k, LIBRARY["catabolite_repression"]["knobs"][k]) for k in ("Ki", "n")},
                        {"glucose": ["glucose"], "lac_repression": ["lac_repression"]}, {"lac_repression": ["lac_repression"]})
    sim = Composite({"state": st}, core=core)
    n = int(round(T_END / DT))
    tr = {k: [] for k in ("t", "glucose", "lactose", "biomass")}
    for i in range(n + 1):
        for k in ("glucose", "lactose", "biomass"):
            tr[k].append(float(sim.state.get(k, 0.0)))
        tr["t"].append(i * DT)
        sim.run(DT)
    return {k: np.array(v) for k, v in tr.items()}


def observe(name, tr):
    G, L, X, t = tr["glucose"], tr["lactose"], tr["biomass"], tr["t"]
    if name == "glucose-consumed": return float(G[-1])
    if name == "lactose-consumed": return float(L[-1])
    if name == "growth":           return float(X.max())
    if name == "diauxic-order":
        idx = np.where(G <= 0.1)[0]
        return float(L[idx[0]]) if len(idx) else float(L[-1])   # lactose still present when glucose is gone
    raise KeyError(name)


TESTS = [
    ("glucose-consumed", "Glucose is consumed", tc.value(0.1, op="<="), "10 mM glucose → ≤0.1"),
    ("lactose-consumed", "Lactose is consumed", tc.value(0.1, op="<="), "10 mM lactose → ≤0.1"),
    ("growth", "Cell grows on BOTH substrates", tc.value(8.0, op=">="), "max biomass ≥ 8 (both yields)"),
    ("diauxic-order", "Glucose is used up BEFORE lactose (sequential)", tc.value(7.0, op=">="),
     "lactose remaining when glucose is depleted ≥ 7 mM — the diauxic shift (Monod 1942)"),
]
BY = {t[0]: t for t in TESTS}


def grade(tr):
    axes = []
    for tid, label, exp, prov in TESTS:
        obs = observe(tid, tr)
        axes.append(tc.check(tid, label, obs, exp, severity="hard", detail={"observed": round(obs, 3), "provenance": prov}))
    return axes


def exp_str(tid):
    e = BY[tid][2]
    return {">=": "≥", "<=": "≤"}.get(e.op, e.op) + f" {e.value}"


QUESTION = ("Build a cell that grows on a mixture of glucose and lactose with the DIAUXIC phenotype: "
            "it consumes glucose first, and only once glucose is exhausted does it switch to lactose — "
            "a sequential shift, not simultaneous co-consumption.")


def navigate(active, knobs, axes):
    """Deterministic worst-negative-margin policy over the authored NAIVE_MAP."""
    fails = sorted([a for a in axes if a["verdict"] == "mismatch"],
                   key=lambda a: (a.get("margin") if a.get("margin") is not None else 0.0))
    if not fails:
        return None
    worst = fails[0]
    mech = NAIVE_MAP.get(worst["id"])
    if mech is None:
        return {"kind": "blocked", "test": worst["id"], "margin": worst.get("margin"),
                "note": f"no mechanism is named for `{worst['id']}` — the policy's map has no move"}
    if mech not in active:
        return {"kind": "install", "test": worst["id"], "margin": worst.get("margin"), "mechanism": mech}
    return {"kind": "blocked", "test": worst["id"], "margin": worst.get("margin"),
            "note": f"`{worst['id']}` still failing with {mech} installed; no knob the policy knows fixes it"}


def run_policy():
    active, knobs = set(), {}
    iterations, prev = [], {}
    st = ls.create(ROOT, "diauxie-policy", QUESTION, max_iterations=12)
    st = ls.lock_tests(st, [{"name": t[0], "pass_if": {"op": t[2].op, "value": t[2].value}} for t in TESTS])
    stall = 0
    for step in range(12):
        tr = simulate(active, knobs)
        axes = grade(tr)
        verd = {a["id"]: a for a in axes}
        n_pass = sum(a["verdict"] == "within_tol" for a in axes)
        passing = {t[0]: verd[t[0]]["verdict"] == "within_tol" for t in TESTS}
        newly = [] if step == 0 else [k for k in passing if passing[k] and not prev.get(k, False)]
        regressed = [k for k in passing if not passing[k] and prev.get(k, False)]
        decision = navigate(active, knobs, axes)
        tests_snap = [{"name": a["id"], "verdict": a["verdict"], "margin": a.get("margin")} for a in axes]
        if step > 0:
            st = ls.record_iteration(st, edit=(prevdec or {}).get("mechanism") or (prevdec or {}).get("note", "edit"),
                                     target="model", margin_deltas={a["id"]: a.get("margin") for a in axes},
                                     gate="pass" if n_pass == len(TESTS) else "fail", tests=tests_snap)
        iterations.append({"iteration": step, "active": sorted(active), "n_pass": n_pass, "n_hard": len(TESTS),
                           "decision": decision, "newly_fixed": newly, "regressed": regressed,
                           "tests": [{"id": a["id"], "label": BY[a["id"]][1], "verdict": a["verdict"],
                                      "observed": a["detail"]["observed"], "expected": exp_str(a["id"]),
                                      "margin": a.get("margin")} for a in axes]})
        prev, prevdec = passing, decision
        if decision is None:
            st = ls.advance(st, "DONE", last_verdict={"gate": "pass"}); return iterations, "DONE", st
        if decision["kind"] == "install":
            active = set(active); active.add(decision["mechanism"]); knobs = dict(knobs); knobs.update(LIBRARY[decision["mechanism"]]["knobs"]); stall = 0
        elif decision["kind"] == "blocked":
            stall += 1
            if stall >= 2:
                st = ls.advance(st, "GIVE_UP", last_verdict={"gate": "fail", "reason": decision["note"]})
                return iterations, "GIVE_UP", st
    st = ls.advance(st, "GIVE_UP", last_verdict={"gate": "fail", "reason": "budget exhausted"})
    return iterations, "GIVE_UP", st


def main():
    os.makedirs(OUT, exist_ok=True)
    iterations, outcome, st = run_policy()
    ls.save(ROOT, "diauxie-policy", st)
    traj = {"schema": "model_build_trajectory/v2", "study": "diauxie", "driver": "deterministic worst-margin policy",
            "contract": QUESTION,
            "tests": [{"id": t[0], "label": t[1], "expected": exp_str(t[0]), "provenance": t[3]} for t in TESTS],
            "iterations": iterations, "result": {"state": outcome, "edits": len(iterations) - 1}}
    with open(os.path.join(OUT, "diauxie_policy_trajectory.json"), "w") as fh:
        json.dump(traj, fh, indent=2)
    print(f"DETERMINISTIC POLICY on diauxie:")
    for it in iterations:
        d = it["decision"]
        act = ("DONE" if d is None else (d["kind"] + ":" + (d.get("mechanism") or "—")))
        fx = f" +{it['newly_fixed']}" if it["newly_fixed"] else ""
        rg = f" REGRESSED {it['regressed']}" if it["regressed"] else ""
        print(f"  iter {it['iteration']} {it['n_pass']}/{it['n_hard']} {it['active']}{fx}{rg} -> {act}")
    print(f"RESULT: {outcome}")
    if outcome == "GIVE_UP":
        print(f"  stuck on: {iterations[-1]['decision'].get('note','')}")


if __name__ == "__main__":
    main()
