"""Data-grounded repair task, rebuilt on COPASI parameter estimation (Fable re-review #2).

The earlier version graded a *recalled* fix — the one model was the celebrity
Elowitz repressilator and the recorded diagnoses reasoned from memorized canonical
values ("KM=80 is exactly double the canonical 40"). That is retrieval, not
diagnosis. This version replaces recall with OPTIMIZATION:

  * The repair is done by running COPASI's Parameter Estimation task
    (`viva_copasi.parameter_estimation.estimate`) to FIT the parameter against the
    intact reference time-course. PE never sees a canonical value — only the
    divergent trace — and recovers the true value by minimizing residual. Recall
    cannot help; the oracle is an optimizer.
  * The reference time-course IS shown (it is the fitting data), not a scalar rmsd.
  * Break ids are OPAQUE (`repair-01/02/03`); the CLI never names the broken
    parameter, so launching a task no longer hands over the diagnosis.
  * A recall-free BASELINE (`localize`): PE fits ALL candidate parameters jointly;
    the one that has to MOVE from its broken value to restore the reference is the
    diagnosed break. "Diagnosis" is now measured against optimization, not against
    a memorized number.

NOTE: the repressilator is retained as the substrate (it is the one bundled model
with fittable *global* quantities), but celebrity-ness no longer helps — the oracle
is PE, not recall. Broadening to a corpus of non-celebrity models is a follow-up
(each needs its own PE window/parameter tuning; the bundled reaction-local models
do not all recover cleanly out of the box).
"""
import os
import warnings

import numpy as np

warnings.filterwarnings("ignore")
import basico  # noqa: E402
from viva_copasi.parameter_estimation import (  # noqa: E402
    estimate, build_experiment_dataframe, resimulation_rmsd,
)

MODEL = os.path.join(os.path.dirname(__file__), os.pardir, os.pardir,
                     "viva-copasi", "viva_copasi", "composites", "repressilator.xml")
_DURATION, _INTERVALS = 100.0, 100
_SPECIES = ["LacI protein", "TetR protein", "cI protein"]
TOL_RMSD = 0.05
_METHOD = "Levenberg - Marquardt"

# candidate parameters the optimizer may fit (the localization search space). None
# of these is revealed as "the broken one" — the CLI break ids are opaque.
_CANDIDATES = ["n", "KM", "translation efficiency"]

# opaque break ids: the id does NOT name the parameter (Fable #2). `blurb`
# describes the biology for the write-up, not for the agent's diagnosis.
BREAKS = {
    "repair-01": {"param": "n", "broken": 1.0,
                  "blurb": "the cooperative-repression Hill coefficient"},
    "repair-02": {"param": "KM", "broken": 80.0,
                  "blurb": "the repression half-saturation constant"},
    "repair-03": {"param": "translation efficiency", "broken": 10.0,
                  "blurb": "the translation efficiency (proteins per transcript)"},
}

_cache = {}   # break_id -> {ref_df, true_params}


def _load():
    basico.load_model(MODEL)


def _ref_df():
    tc = basico.run_time_course(duration=_DURATION, intervals=_INTERVALS)
    return build_experiment_dataframe(tc, species=_SPECIES)


def _reference(break_id):
    """Cache the intact reference trace (the fitting data) + the true parameter table."""
    if break_id not in _cache:
        _load()
        df = basico.get_parameters()
        true_params = {p: round(float(df.loc[p, "value"]), 4) for p in _CANDIDATES}
        _cache[break_id] = {"ref_df": _ref_df(), "true_params": true_params}
    return _cache[break_id]


def _apply(param, value):
    basico.set_parameters(name=param, exact=True, initial_value=float(value))


def _broken_model(break_id):
    _load()
    _apply(BREAKS[break_id]["param"], BREAKS[break_id]["broken"])


def _rmsd_vs_reference(ref_df):
    """RMSD of the CURRENT model's trace vs the reference df (pooled over species)."""
    cur = _ref_df()
    num = den = 0.0
    for s in _SPECIES:
        num += float(np.mean((cur[s].to_numpy() - ref_df[s].to_numpy()) ** 2))
        den += float(np.ptp(ref_df[s].to_numpy()) ** 2) or 1.0
    return float(np.sqrt(num / max(den, 1e-9)))


def _displayed_params(break_id, overrides=None):
    r = _reference(break_id)
    tbl = dict(r["true_params"])
    tbl[BREAKS[break_id]["param"]] = BREAKS[break_id]["broken"]
    for k, v in (overrides or {}).items():
        tbl[k] = round(float(v), 4)
    return tbl


def _trace_summary(df):
    """A compact, SHOWN view of a time-course (the divergence the agent reasons from)."""
    t = df["Time"].to_numpy()
    idx = np.linspace(0, len(t) - 1, 6).astype(int)
    return {"time": [round(float(t[i]), 2) for i in idx],
            "series": {s: [round(float(df[s].to_numpy()[i]), 3) for i in idx] for s in _SPECIES}}


def broken_state(break_id="repair-01"):
    """The broken model as the agent sees it: parameter table, the reference AND
    broken time-courses (the divergence is SHOWN), and the rmsd."""
    r = _reference(break_id)
    _broken_model(break_id)
    broken_df = _ref_df()
    return {"parameters": _displayed_params(break_id),
            "candidate_parameters": list(_CANDIDATES),
            "reference_trace": _trace_summary(r["ref_df"]),
            "broken_trace": _trace_summary(broken_df),
            "rmsd_vs_reference": round(_rmsd_vs_reference(r["ref_df"]), 4),
            "note": "The model diverges from its reference time-course (both shown). Repair it: either "
                    "set a parameter directly, or run parameter estimation (`fit`) to recover it against "
                    "the reference — the reference is the ground truth, no canonical value is given."}


def repair(break_id, param, value):
    """Manual repair: set `param` to `value`, grade by rmsd vs the reference trace."""
    r = _reference(break_id)
    if param not in r["true_params"]:
        return {"error": f"unknown parameter {param!r}", "available": list(_CANDIDATES)}
    _broken_model(break_id)
    _apply(param, value)
    rmsd = _rmsd_vs_reference(r["ref_df"])
    return {"param": param, "value": float(value), "rmsd_vs_reference": round(rmsd, 4),
            "matched": rmsd < TOL_RMSD}


def _broken_vals(break_id):
    """The parameter values in the BROKEN model, computed from known values (not via
    the unreliable get_parameters read-back): every candidate at its true value
    except the broken one, which is at BREAKS[...]['broken']."""
    r = _reference(break_id)
    vals = dict(r["true_params"])
    vals[BREAKS[break_id]["param"]] = float(BREAKS[break_id]["broken"])
    return vals


def _fit_items(candidates, break_id):
    """Fit items with bounds around each candidate's true magnitude, started from
    the known BROKEN value so the optimizer must move the broken one."""
    r = _reference(break_id)
    broken = _broken_vals(break_id)
    items = []
    for p in candidates:
        true = r["true_params"][p]
        items.append({"name": p, "lower": true * 0.1, "upper": true * 5 or 1.0, "start": broken[p]})
    return items


def fit(break_id, candidates=None):
    """Run COPASI parameter estimation to repair the break by OPTIMIZATION against
    the reference trace. `candidates` defaults to just the (hidden) broken parameter
    for a direct fit; pass a list to fit several at once."""
    r = _reference(break_id)
    cands = candidates or [BREAKS[break_id]["param"]]
    cands = [c for c in cands if c in r["true_params"]]
    if not cands:
        return {"error": "no known candidate parameters", "available": list(_CANDIDATES)}
    _broken_model(break_id)
    res = estimate(basico.get_current_model(), r["ref_df"], _fit_items(cands, break_id), method=_METHOD)
    rmsd = resimulation_rmsd(res["model"], r["ref_df"], species=_SPECIES)
    fitted = {c: round(res["fitted"][f"Values[{c}]"], 4) for c in cands}
    return {"fitted": fitted, "resim_rmsd": round(rmsd, 6), "objective": res["objective"],
            "matched": rmsd < TOL_RMSD, "method": _METHOD}


def localize(break_id):
    """Recall-free BASELINE: fit ALL candidate parameters jointly; the one that has
    to MOVE from its broken value to restore the reference is the diagnosed break.
    Diagnosis by optimization — no canonical value consulted."""
    r = _reference(break_id)
    _broken_model(break_id)
    broken_vals = _broken_vals(break_id)
    res = estimate(basico.get_current_model(), r["ref_df"], _fit_items(_CANDIDATES, break_id), method=_METHOD)
    moved = {p: round(abs(res["fitted"][f"Values[{p}]"] - broken_vals[p]), 4) for p in _CANDIDATES}
    diagnosed = max(moved, key=moved.get)
    rmsd = resimulation_rmsd(res["model"], r["ref_df"], species=_SPECIES)
    return {"diagnosed_parameter": diagnosed,
            "moved_from_broken": moved,
            "fitted": {p: round(res["fitted"][f"Values[{p}]"], 4) for p in _CANDIDATES},
            "resim_rmsd": round(rmsd, 6),
            "correct": diagnosed == BREAKS[break_id]["param"],
            "note": "PE fit all candidates jointly; only the broken parameter had to move to restore the "
                    "reference. This diagnosis used optimization against the trace, not any recalled value."}


if __name__ == "__main__":
    for bid, spec in BREAKS.items():
        bs = broken_state(bid)
        f = fit(bid)
        loc = localize(bid)
        print(f"{bid}  (break {spec['param']}={spec['broken']}, {spec['blurb']})")
        print(f"   broken rmsd={bs['rmsd_vs_reference']}  fit->{f['fitted']} resimRMSD={f['resim_rmsd']} matched={f['matched']}")
        print(f"   localize (recall-free): diagnosed={loc['diagnosed_parameter']} correct={loc['correct']} "
              f"moved={loc['moved_from_broken']}")
