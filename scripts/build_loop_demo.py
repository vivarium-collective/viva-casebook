"""Study-automation pipeline demo: drive ONE study through the whole agentic
model-building loop and capture the REAL, EMERGENT trajectory.

The trajectory is NOT scripted. A deterministic NAVIGATE policy reads the graded
tests each iteration, takes the failing HARD test with the most-negative margin,
and either installs the mechanism that test pulls on (from a small library, with
literature-grounded default knobs) or takes one calibration step on its knob.
The iteration count, the mass-balance rejection of an under-specified model, the
thermal-tolerance regression, and the recovery are all consequences of that
policy — not a hand-authored list. Every verdict is computed by running the
model version and grading it with `viva_superpowers.test_contract`.

Also captures: a two-round sufficiency audit (one-sided bands flagged → revised
to two-sided → re-audit), an explicitly graded negative control, a GIVE_UP
companion trace (thermal mechanism withheld), and perturbation-stability of the
final pass. Writes trajectory.json + a real .pbg/loop/bounded-cell.json.

Toy-real: the rate-law SHAPES are real (Monod uptake, yield-coupled growth, mass
balance, threshold thermal death); the constants are illustrative, grounded in
E. coli M9-glucose magnitudes (see CITES) but not fitted.
"""
import copy
import json
import os

import numpy as np

from viva_superpowers import loop_state as ls, test_contract as tc, test_audit

HERE = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(HERE, os.pardir))
OUT = os.path.join(ROOT, "workspace", "investigations", "model-building")

CITES = {
    "monod": "Monod 1949, Annu Rev Microbiol (uptake shape); Senn et al. 1994 BBA (Ks ~ µM glucose)",
    "yield": "biomass yield Y ≈ 0.4–0.5 gDW/g glucose, E. coli aerobic M9",
    "mumax": "µmax ≈ 0.6–0.7 h⁻¹, E. coli M9 glucose 37 °C",
    "thermal": "Ratkowsky et al. 1982 J Bacteriol; Rosso et al. 1993 J Theor Biol (Tmax ≈ 45–47 °C)",
}

# ── Mechanism / knob library (invariant I3: provided mechanisms only) ─────────
# Each mechanism, once installed, contributes to the dynamics with its knobs.
# Defaults are priors; NAVIGATE may calibrate a knob against a failing test.
LIBRARY = {
    "monod_uptake":  {"knobs": {"qmax": 3.0, "Ks": 0.02}, "cite": CITES["monod"]},
    "yield_growth":  {"knobs": {"Y": 0.45}, "cite": CITES["yield"]},
    "thermal_death": {"knobs": {"t_tol": 35.0, "k_death": 0.8}, "cite": CITES["thermal"]},
}

# Which mechanism each test pulls on (NAVIGATE's map from a failing test → an edit).
TEST_MECH = {
    "nutrient-depletion": "monod_uptake",
    "growth":             "yield_growth",   # growth is only credible if yield-coupled
    "conservation":       "yield_growth",
    "viability-cliff":    "thermal_death",
    "viability-in-band":  "thermal_death",
}

T_END, DT = 8.0, 0.02          # hours
N0, X0 = 10.0, 0.5             # mM glucose, gDW/L (toy scale)
Y_REF = 0.45                   # the mass-balance reference yield the conservation test enforces


def simulate(active, knobs, *, dt=DT):
    t = np.arange(0.0, T_END + dt, dt)
    n = len(t)
    X = np.zeros(n); N = np.zeros(n); th = np.zeros(n)
    temp = 37.0 + (50.0 - 37.0) * (t / T_END)      # ramp 37 → 50 °C
    X[0], N[0], th[0] = X0, N0, 1.0
    qmax = knobs.get("qmax", 3.0); Ks = knobs.get("Ks", 0.02)
    Y = knobs.get("Y", 0.45); t_tol = knobs.get("t_tol"); k_death = knobs.get("k_death", 0.8)
    for i in range(1, n):
        # specific uptake q (per biomass) × biomass X = total uptake (Monod, biomass-coupled)
        q = (qmax * N[i-1] / (Ks + N[i-1])) if ("monod_uptake" in active and N[i-1] > 0) else 0.0
        uptake = q * X[i-1]
        grow = (Y * uptake) if "yield_growth" in active else 0.0
        X[i] = X[i-1] + grow * dt
        N[i] = max(0.0, N[i-1] - uptake * dt)
        if "thermal_death" in active and t_tol is not None:
            th[i] = max(0.0, th[i-1] - k_death * max(0.0, temp[i-1] - t_tol) * th[i-1] * dt)
        else:
            th[i] = th[i-1]
    return {"t": t, "biomass": X, "nutrient": N, "viability": th, "temperature": temp, "Y": Y}


def observe(name, out):
    X, N, th, t = out["biomass"], out["nutrient"], out["viability"], out["t"]
    if name == "growth":             return float(X.max())
    if name == "nutrient-depletion": return float(N[-1])
    if name == "viability-cliff":    return float(th[-1])
    if name == "viability-in-band":  return float(th[int(np.argmin(np.abs(t - 3.0)))])
    if name == "conservation":       return float((X.max() - X[0]) - Y_REF * (N[0] - N[-1]))
    if name == "saturation":         # fraction of final biomass reached by t=6 h
        i6 = int(np.argmin(np.abs(t - 6.0))); return float(X[i6] / X[-1]) if X[-1] > X0 else 1.0
    raise KeyError(name)


# ── Acceptance tests. `expected` is the LOCKED (two-sided) form; `oneside` is
# the initial one-sided draft the audit flags in round 1. ─────────────────────
TESTS = [
    dict(id="growth", label="Cell grows well above seed, within the yield ceiling",
         expected=tc.band(2.0, 5.5), oneside=tc.value(2.0, op=">="), sev="hard",
         knob="yield_growth", cell=None,
         prov="≥2× seed AND ≤ yield ceiling X₀+Y·N₀=5.0 gDW/L — a model may not create mass (%s)" % CITES["yield"]),
    dict(id="nutrient-depletion", label="Monod uptake draws the pool to ≈0",
         expected=tc.band(0.0, 0.1), oneside=tc.value(0.1, op="<="), sev="hard",
         knob="monod_uptake",
         prov="10 mM glucose drawn to ≤0.1 mM and non-negative (%s)" % CITES["monod"]),
    dict(id="conservation", label="Growth is paid for by nutrient (mass balance)",
         expected=tc.band(-0.25, 0.25), oneside=tc.band(-0.25, 0.25), sev="hard",
         knob="yield_growth",
         prov="|ΔX − Y·ΔN| ≤ 0.25, Y=0.45 gDW/g — falsifies uptake-without-yield-coupled-growth (%s)" % CITES["yield"]),
    dict(id="viability-cliff", label="Viability collapses past the tolerance",
         expected=tc.band(0.0, 0.1), oneside=tc.value(0.1, op="<="), sev="hard",
         knob="thermal_death",
         prov="θ→0 once T>t_tol on the ramp (%s)" % CITES["thermal"]),
    dict(id="viability-in-band", label="Viability holds while below tolerance",
         expected=tc.band(0.9, 1.0), oneside=tc.value(0.9, op=">="), sev="hard",
         knob="thermal_death",
         prov="θ≥0.9 at t=3 h while T<t_tol (%s)" % CITES["thermal"]),
    dict(id="saturation", label="Growth saturates before the run ends",
         expected=tc.value(0.9, op=">="), oneside=tc.value(0.9, op=">="), sev="directional",
         knob="monod_uptake",
         prov="≥90% of final biomass reached by t=6 h (substrate-limited batch saturates)"),
]
BYID = {t["id"]: t for t in TESTS}


def grade(out, *, use_locked=True):
    axes = []
    for t in TESTS:
        exp = t["expected"] if use_locked else t["oneside"]
        obs = observe(t["id"], out)
        ax = tc.check(t["id"], t["label"], obs, exp, severity=t["sev"], knob=t["knob"],
                      detail={"observed": round(obs, 4), "provenance": t["prov"]})
        axes.append(ax)
    return axes


def expected_str(t):
    e = t["expected"]
    sym = {">=": "≥", "<=": "≤", "==": "="}
    return f"∈ [{e.low}, {e.high}]" if e.kind == "band" else f"{sym.get(e.op, e.op)} {e.value}"


QUESTION = ("Build a bounded, goal-directed cell: on a finite nutrient pool and a rising "
            "temperature, produce a cell whose BIOMASS grows on the nutrient it CONSUMES "
            "(mass-conserving, Monod-saturating GROWTH), and whose VIABILITY holds while "
            "below its temperature tolerance then collapses once temperature exceeds it.")


def build_spec(use_locked=True):
    bt = []
    for t in TESTS:
        e = t["expected"] if use_locked else t["oneside"]
        pass_if = ({"op": e.op, "value": e.value} if e.kind == "value"
                   else {"op": "in", "value": [e.low, e.high]})
        bt.append({"name": t["id"], "classification": "primary" if t["sev"] == "hard" else "diagnostic",
                   "description": t["label"], "measure": {"observable": t["id"], "knob": t["knob"]},
                   "pass_if": {**pass_if, "provenance": t["prov"]}})
    bt.append({"name": "draft-is-inert", "classification": "diagnostic", "control": "negative",
               "description": "The inert draft MUST fail growth — the negative control the built model is contrasted against.",
               "measure": {"observable": "growth"},
               "pass_if": {"op": "in", "value": [2.0, 5.5], "provenance": "inert draft: max(biomass)=0.5 → fails"}})
    return {"name": "bounded-cell", "question": QUESTION, "behavior_tests": bt}


# ── NAVIGATE: deterministic policy over the graded axes ──────────────────────
def navigate(active, knobs, axes, library):
    hard_fail = sorted([a for a in axes if a.get("severity") == "hard" and a["verdict"] == "mismatch"],
                       key=lambda a: (a.get("margin") if a.get("margin") is not None else 0.0))
    if not hard_fail:
        return None
    worst = hard_fail[0]
    mech = TEST_MECH[worst["id"]]
    if mech not in active:
        if mech not in library:
            return {"kind": "blocked", "test": worst["id"], "margin": worst.get("margin"),
                    "mechanism": mech, "note": f"no available mechanism provides `{worst['id']}` — cannot proceed"}
        return {"kind": "install", "test": worst["id"], "margin": worst.get("margin"), "mechanism": mech,
                "detail": f"worst hard failure `{worst['id']}` (margin {round(worst.get('margin',0),3)}) → install {mech}"}
    # installed → calibrate its knob toward the failing margin (thermal tolerance)
    if mech == "thermal_death":
        step = 3.5
        old = knobs["t_tol"]
        new = old + step if worst["id"] == "viability-in-band" else old - step   # raise if in-band fails, lower if cliff fails
        return {"kind": "calibrate", "test": worst["id"], "margin": worst.get("margin"), "mechanism": mech,
                "knob": "t_tol", "from": round(old, 2), "to": round(new, 2),
                "detail": f"`{worst['id']}` still failing (margin {round(worst.get('margin',0),3)}) → step t_tol {round(old,1)}→{round(new,1)} °C"}
    # an installed, non-calibratable mechanism that still fails means the library
    # cannot satisfy this test — the loop is stuck (drives an honest GIVE_UP).
    return {"kind": "blocked", "test": worst["id"], "margin": worst.get("margin"), "mechanism": mech,
            "note": f"`{worst['id']}` still failing with {mech} installed and no calibratable knob"}


def run_loop(library, *, tag, st=None):
    """Walk BUILD→RUN→EVALUATE→DECIDE→NAVIGATE until DONE or budget/stall → GIVE_UP.
    Returns (iterations, final_state, final_out, per_iter_viability)."""
    active, knobs = set(), {}
    iterations, viab_series = [], []
    stall = 0
    budget = st["budget"]["max_iterations"] if st else 12
    prev_pass, prev_margins = {}, {}
    final_out = None
    for step in range(budget + 1):
        out = simulate(active, knobs)
        final_out = out
        axes = grade(out)
        viab_series.append([round(float(v), 4) for v in out["viability"][::12]])
        verdicts = {a["id"]: a for a in axes}
        hard = [t["id"] for t in TESTS if t["sev"] == "hard"]
        n_pass = sum(verdicts[h]["verdict"] == "within_tol" for h in hard)
        passing = {h: (verdicts[h]["verdict"] == "within_tol") for h in hard}
        newly = [h for h in hard if passing[h] and not prev_pass.get(h, True if step == 0 else False)]
        if step == 0:
            newly = []   # iteration 0 has no "fixed" — its passes are baseline
        regressed = [h for h in hard if not passing[h] and prev_pass.get(h, False)]
        margins = {a["id"]: a.get("margin") for a in axes}
        decision = navigate(active, knobs, axes, library)
        if st is not None:
            st = ls.record_iteration(st, edit=(decision or {}).get("detail", "all hard tests pass → DONE"),
                                     target="model", margin_deltas={k: (None if margins[k] is None or prev_margins.get(k) is None
                                     else round(margins[k]-prev_margins[k], 4)) for k in margins},
                                     gate="pass" if n_pass == len(hard) else "fail")
        iterations.append({
            "iteration": step,
            "active": sorted(active), "knobs": {k: round(v, 3) for k, v in knobs.items()},
            "n_pass": n_pass, "n_hard": len(hard),
            "verdicts": [{"id": a["id"], "label": BYID[a["id"]]["label"], "severity": a.get("severity"),
                          "verdict": a["verdict"], "observed": a["detail"]["observed"],
                          "expected": expected_str(BYID[a["id"]]), "margin": a.get("margin")} for a in axes],
            "newly_fixed": newly, "regressed": regressed,
            "decision": decision,
        })
        prev_pass, prev_margins = passing, margins
        if decision is None:
            st = ls.advance(st, "DONE", last_verdict={"gate": "pass"}) if st is not None else st
            return iterations, st, final_out, viab_series, "DONE"
        # apply the edit (BUILD)
        if decision["kind"] == "install":
            active.add(decision["mechanism"])
            knobs.update(library[decision["mechanism"]]["knobs"])
            stall = 0
        elif decision["kind"] == "calibrate":
            knobs[decision["knob"]] = decision["to"]; stall = 0
        elif decision["kind"] == "blocked":
            stall += 1
            if stall >= 2:
                st = ls.advance(st, "GIVE_UP", last_verdict={"gate": "fail", "reason": decision["note"]}) if st is not None else st
                return iterations, st, final_out, viab_series, "GIVE_UP"
    st = ls.advance(st, "GIVE_UP", last_verdict={"gate": "fail", "reason": "budget exhausted"}) if st is not None else st
    return iterations, st, final_out, viab_series, "GIVE_UP"


def perturbation_stability(final_active, final_knobs):
    """Re-grade the final model under dt/2 and ±10% on each knob; count stable passes."""
    hard = [t["id"] for t in TESTS if t["sev"] == "hard"]
    def all_pass(active, knobs, dt):
        out = simulate(active, knobs, dt=dt)
        ax = {a["id"]: a for a in grade(out)}
        return all(ax[h]["verdict"] == "within_tol" for h in hard)
    variants = [("dt/2", final_active, final_knobs, DT/2)]
    for k in final_knobs:
        for f, lbl in ((1.1, "+10%"), (0.9, "−10%")):
            kk = dict(final_knobs); kk[k] = kk[k]*f
            variants.append((f"{k} {lbl}", final_active, kk, DT))
    stable = sum(all_pass(a, kn, dt) for _l, a, kn, dt in variants)
    return {"stable": stable, "total": len(variants),
            "variants": [{"perturbation": l, "pass": all_pass(a, kn, dt)} for l, a, kn, dt in variants]}


def main():
    os.makedirs(OUT, exist_ok=True)

    # AUTHOR → AUDIT round 1 (one-sided bands) → revise → AUDIT round 2 (two-sided) → SELECT → LOCK
    spec1 = build_spec(use_locked=False)
    rep1 = test_audit.build_audit_report(spec1); gate1 = test_audit.audit_gate(rep1)
    spec = build_spec(use_locked=True)
    rep2 = test_audit.build_audit_report(spec); gate2 = test_audit.audit_gate(rep2)

    st = ls.create(ROOT, "bounded-cell", QUESTION, max_iterations=12)
    st = ls.advance(st, "AUDIT", audit={"gate": gate2, "reopened_from": gate1})
    st = ls.advance(st, "SELECT", sourcing={"decision": "build-new", "modules": [],
                    "rationale": "no catalogued module implements a bounded, goal-directed cell", "gate": "pass"})
    st = ls.lock_tests(st, spec["behavior_tests"])
    locked_hash = st.get("locked_tests_hash")

    # explicit negative control: the inert draft must FAIL growth
    ctrl_out = simulate(set(), {})
    ctrl_ax = grade(ctrl_out)[0]   # growth axis on the inert model
    control = {"test": "draft-is-inert", "observed": ctrl_ax["detail"]["observed"],
               "expected": expected_str(BYID["growth"]), "discriminates": ctrl_ax["verdict"] == "mismatch"}

    # the real emergent build loop
    iterations, st, final_out, viab_series, outcome = run_loop(LIBRARY, tag="full", st=st)
    for it, vs in zip(iterations, viab_series):
        it["viability_curve"] = vs
    violations = ls.validate(st, spec["behavior_tests"])
    ls.save(ROOT, "bounded-cell", st)

    # GIVE_UP companion: withhold the thermal mechanism
    lib_no_thermal = {k: v for k, v in LIBRARY.items() if k != "thermal_death"}
    gu_iters, _s, _o, _v, gu_outcome = run_loop(lib_no_thermal, tag="giveup", st=None)

    # perturbation stability of the final model
    final_active = set(iterations[-1]["active"]); final_knobs = dict(iterations[-1]["knobs"])
    stability = perturbation_stability(final_active, final_knobs)

    def ds(a, m=100):
        idx = np.linspace(0, len(a)-1, m).astype(int)
        return [round(float(a[i]), 4) for i in idx]

    # cliff time: where temperature crosses the final calibrated tolerance
    t_tol_final = final_knobs.get("t_tol")
    cliff_frac = ((t_tol_final - 37.0) / 13.0) if t_tol_final else None

    traj = {
        "schema": "model_build_trajectory/v2",
        "study": "bounded-cell",
        "contract": {"question": QUESTION,
                     "observables": ["biomass (gDW/L)", "nutrient (mM glucose)", "viability", "temperature (°C, driven)"],
                     "success": "all 5 hard acceptance tests pass; 1 directional test rides along"},
        "draft": {"description": "Typed exchange ports declared with no mechanism behind them — the inert "
                                 "starting point the loop must compile into a running cell.",
                  "ports": ["biomass", "nutrient", "viability", "temperature (driven)"]},
        "select": {"decision": "build-new", "rationale": "no catalogued module implements a bounded, goal-directed cell",
                   "library": [{"mechanism": m, "knobs": list(v["knobs"]), "cite": v["cite"]} for m, v in LIBRARY.items()]},
        "audit": {"round1_gate": gate1, "round2_gate": gate2,
                  "revision": "one-sided thresholds flagged (discrimination drift) → revised to two-sided bands "
                              "justified by the yield ceiling X₀+Y·N₀ (a model may not create mass) → re-audit",
                  "axes": [{"id": a["id"], "label": a.get("label"), "verdict": a["verdict"]}
                           for g in rep2.get("groups", {}).values() for a in g.get("axes", [])],
                  "round1_flags": [{"id": a["id"], "verdict": a["verdict"]}
                                   for g in rep1.get("groups", {}).values() for a in g.get("axes", []) if a["verdict"] != "within_tol"]},
        "control": control,
        "lock": {"tests_hash": locked_hash, "n_tests_locked": len(spec["behavior_tests"]),
                 "n_hard": sum(1 for t in TESTS if t["sev"] == "hard"),
                 "reopen_count": int(st.get("reopen_count", 0)),
                 "prior_hashes": (st.get("prereg_record") or {}).get("prior_hashes", [])},
        "tests": [{"id": t["id"], "label": t["label"], "expected": expected_str(t), "severity": t["sev"],
                   "knob": t["knob"], "provenance": t["prov"]} for t in TESTS],
        "iterations": iterations,
        "result": {"state": outcome, "edits_to_pass": len(iterations)-1,
                   "budget_spent": st["budget"]["spent"], "max_iterations": st["budget"]["max_iterations"],
                   "violations": violations, "final_knobs": {k: round(v, 3) for k, v in final_knobs.items()},
                   "stability": stability},
        "giveup_companion": {"outcome": gu_outcome, "final_pass": gu_iters[-1]["n_pass"], "n_hard": gu_iters[-1]["n_hard"],
                             "note": "same loop with the thermal mechanism withheld — it improves to the ceiling the "
                                     "library allows, then terminates HONESTLY (GIVE_UP) instead of faking a pass"},
        "timeseries": {"t": ds(final_out["t"]), "biomass": ds(final_out["biomass"]),
                       "nutrient": ds(final_out["nutrient"]), "viability": ds(final_out["viability"]),
                       "temperature": ds(final_out["temperature"]), "cliff_frac": cliff_frac, "t_tol": t_tol_final},
    }
    path = os.path.join(OUT, "trajectory.json")
    with open(path, "w") as fh:
        json.dump(traj, fh, indent=2)

    print(f"AUDIT: round1={gate1} → revised → round2={gate2}   LOCK: {traj['lock']['n_tests_locked']} tests ({locked_hash[:12]}…)")
    print(f"CONTROL draft-is-inert discriminates: {control['discriminates']} (growth obs {control['observed']})")
    for it in iterations:
        d = it["decision"]
        tail = f"  → {d['kind']}:{d.get('mechanism','')}" if d else "  → DONE"
        fx = f" +{it['newly_fixed']}" if it["newly_fixed"] else ""
        rg = f" REGRESSED {it['regressed']}" if it["regressed"] else ""
        print(f"  iter {it['iteration']} {it['n_pass']}/{it['n_hard']} active={it['active']}{fx}{rg}{tail}")
    print(f"RESULT: {outcome} in {len(iterations)-1} edits; violations={violations}; "
          f"stability {stability['stable']}/{stability['total']}")
    print(f"GIVE_UP companion: {gu_outcome} at {gu_iters[-1]['n_pass']}/{gu_iters[-1]['n_hard']}")
    print(f"trajectory -> {os.path.relpath(path, ROOT)}")


if __name__ == "__main__":
    main()
