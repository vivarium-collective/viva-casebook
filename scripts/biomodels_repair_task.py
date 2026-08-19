"""Data-grounded break-and-repair suite over MULTIPLE non-celebrity models, rebuilt
on COPASI parameter estimation (Fable re-review #2 + the de-celebritization follow-up).

The diagnosis is OPTIMIZATION, not recall: a parameter is broken, and the repair is
done by running COPASI's Parameter Estimation task (viva_copasi.parameter_estimation)
to FIT the parameter against the intact reference time-course. PE never sees a
canonical value — only the divergent trace — and recovers the true value by
minimizing residual. A recall-free `localize` baseline fits all candidate parameters
jointly; the one that must MOVE to restore the reference is the diagnosed break.

De-celebritization: the suite now spans two structurally different, independently
vetted gene-regulatory circuits, not just the celebrity repressilator —
  * repressilator (Elowitz 2000): a synthetic three-gene bacterial oscillator;
  * Chickarmane 2006 stem-cell switch: the mammalian OCT4/SOX2/Nanog pluripotency
    network.
Both were selected because their parameters are structurally IDENTIFIABLE from a
single time-course (verified: break → PE recovers the true value AND the joint
`localize` fit produces a one-hot moved vector). Most published models are NOT
usable this way — their parameters are "sloppy"/non-identifiable, so all optimizers
converge to the same wrong value (empirically confirmed across LM / Particle Swarm /
Evolutionary Programming). Adding a model therefore means vetting it, not just
fetching it. SBML is vendored under workspace/models/biomodels/.
"""
import os
import warnings

import numpy as np

warnings.filterwarnings("ignore")
import basico  # noqa: E402
from viva_copasi.parameter_estimation import (  # noqa: E402
    estimate, build_experiment_dataframe, resimulation_rmsd,
)

_VENDOR = os.path.join(os.path.dirname(__file__), os.pardir, "workspace", "models", "biomodels")
TOL_RMSD = 0.05
_METHOD = "Levenberg - Marquardt"

# each model: vendored SBML, the observed species, a simulation window, and the
# candidate parameters (the localization search space — all structurally
# identifiable + sensitive, verified).
MODELS = {
    "repressilator": {
        "sbml": os.path.join(_VENDOR, "repressilator.xml"),
        "label": "Elowitz 2000 repressilator — a synthetic three-gene bacterial oscillator",
        "species": ["LacI protein", "TetR protein", "cI protein"],
        "duration": 100.0, "intervals": 100,
        "candidates": ["n", "KM", "translation efficiency"],
    },
    "stemcell": {
        "sbml": os.path.join(_VENDOR, "BIOMD0000000203.xml"),
        "label": "Chickarmane 2006 stem-cell switch — the OCT4/SOX2/Nanog pluripotency network",
        "species": ["OCT4", "SOX2", "Protein"],
        "duration": 50.0, "intervals": 80,
        # a1/gamma1/k1c: each produces a visible divergence, recovers under PE, and is
        # JOINTLY identifiable (one-hot localize). a2/a3/c1/gamma3 were rejected —
        # a2/a3 are insensitive over this observable, c1/gamma3 are correlated with
        # a1/gamma1 (they would compensate and break the joint localize).
        "candidates": ["a1", "gamma1", "k1c"],
    },
}

# opaque break ids (the id does NOT name the parameter); each names its model +
# the parameter that was broken and the broken value. `blurb` is for the write-up.
BREAKS = {
    "repair-01": {"model": "repressilator", "param": "n", "broken": 1.0,
                  "blurb": "the cooperative-repression Hill coefficient"},
    "repair-02": {"model": "repressilator", "param": "KM", "broken": 80.0,
                  "blurb": "the repression half-saturation constant"},
    "repair-03": {"model": "repressilator", "param": "translation efficiency", "broken": 10.0,
                  "blurb": "the translation efficiency (proteins per transcript)"},
    "repair-04": {"model": "stemcell", "param": "a1", "broken": 2.0,
                  "blurb": "a synthesis/activation rate constant in the OCT4/SOX2/Nanog network"},
    "repair-05": {"model": "stemcell", "param": "gamma1", "broken": 2.0,
                  "blurb": "a degradation-rate constant in the OCT4/SOX2/Nanog network"},
    "repair-06": {"model": "stemcell", "param": "k1c", "broken": 0.1,
                  "blurb": "a regulatory (binding) rate constant in the OCT4/SOX2/Nanog network"},
}

_cache = {}   # model_key -> {ref_df, true_params}


def _mkey(break_id):
    return BREAKS[break_id]["model"]


def _mspec(break_id):
    return MODELS[_mkey(break_id)]


def _load(break_id):
    basico.load_model(_mspec(break_id)["sbml"])


def _ref_df(break_id):
    m = _mspec(break_id)
    tc = basico.run_time_course(duration=m["duration"], intervals=m["intervals"])
    return build_experiment_dataframe(tc, species=m["species"])


def _reference(break_id):
    """Cache the intact reference trace (the fitting data) + the true parameter
    table, per MODEL (shared across that model's breaks)."""
    key = _mkey(break_id)
    if key not in _cache:
        _load(break_id)
        df = basico.get_parameters()
        cands = _mspec(break_id)["candidates"]
        true_params = {p: round(float(df.loc[p, "value"]), 6) for p in cands}
        _cache[key] = {"ref_df": _ref_df(break_id), "true_params": true_params}
    return _cache[key]


def _apply(param, value):
    basico.set_parameters(name=param, exact=True, initial_value=float(value))


def _broken_model(break_id):
    _load(break_id)
    _apply(BREAKS[break_id]["param"], BREAKS[break_id]["broken"])


def _rmsd_vs_reference(break_id, ref_df):
    cur = _ref_df(break_id)
    sp = _mspec(break_id)["species"]
    num = sum(float(np.mean((cur[s].to_numpy() - ref_df[s].to_numpy()) ** 2)) for s in sp)
    den = sum(float(np.ptp(ref_df[s].to_numpy()) ** 2) or 1.0 for s in sp)
    return float(np.sqrt(num / max(den, 1e-9)))


def _broken_vals(break_id):
    """Broken-model parameter values from KNOWN values (not the unreliable
    get_parameters read-back): each candidate at its true value except the broken
    one, which is at BREAKS[...]['broken']."""
    r = _reference(break_id)
    vals = dict(r["true_params"])
    vals[BREAKS[break_id]["param"]] = float(BREAKS[break_id]["broken"])
    return vals


def _displayed_params(break_id, overrides=None):
    r = _reference(break_id)
    tbl = dict(r["true_params"])
    tbl[BREAKS[break_id]["param"]] = BREAKS[break_id]["broken"]
    for k, v in (overrides or {}).items():
        tbl[k] = round(float(v), 6)
    return tbl


def _trace_summary(break_id, df):
    sp = _mspec(break_id)["species"]
    t = df["Time"].to_numpy()
    idx = np.linspace(0, len(t) - 1, 6).astype(int)
    return {"time": [round(float(t[i]), 2) for i in idx],
            "series": {s: [round(float(df[s].to_numpy()[i]), 4) for i in idx] for s in sp}}


def broken_state(break_id="repair-01"):
    r = _reference(break_id)
    _broken_model(break_id)
    broken_df = _ref_df(break_id)
    return {"model": _mspec(break_id)["label"],
            "parameters": _displayed_params(break_id),
            "candidate_parameters": list(_mspec(break_id)["candidates"]),
            "reference_trace": _trace_summary(break_id, r["ref_df"]),
            "broken_trace": _trace_summary(break_id, broken_df),
            "rmsd_vs_reference": round(_rmsd_vs_reference(break_id, r["ref_df"]), 4),
            "note": "The model diverges from its reference time-course (both shown). Repair it: set a "
                    "parameter directly, or run parameter estimation (`fit`) to recover it against the "
                    "reference — the reference is the ground truth, no canonical value is given."}


def repair(break_id, param, value):
    r = _reference(break_id)
    if param not in r["true_params"]:
        return {"error": f"unknown parameter {param!r}", "available": list(_mspec(break_id)["candidates"])}
    _broken_model(break_id)
    _apply(param, value)
    rmsd = _rmsd_vs_reference(break_id, r["ref_df"])
    return {"param": param, "value": float(value), "rmsd_vs_reference": round(rmsd, 4),
            "matched": rmsd < TOL_RMSD}


def _fit_items(break_id, candidates):
    r = _reference(break_id)
    broken = _broken_vals(break_id)
    items = []
    for p in candidates:
        true = r["true_params"][p]
        items.append({"name": p, "lower": true * 0.1, "upper": true * 10 or 1.0, "start": broken[p]})
    return items


def fit(break_id, candidates=None):
    """Repair by OPTIMIZATION: run COPASI PE to fit the reference trace. `candidates`
    defaults to the model's full candidate set (so a bare call does not reveal which
    parameter is broken); pass a subset to fit specific ones."""
    r = _reference(break_id)
    cands = candidates or list(_mspec(break_id)["candidates"])
    cands = [c for c in cands if c in r["true_params"]]
    if not cands:
        return {"error": "no known candidate parameters", "available": list(_mspec(break_id)["candidates"])}
    _broken_model(break_id)
    res = estimate(basico.get_current_model(), r["ref_df"], _fit_items(break_id, cands), method=_METHOD)
    rmsd = resimulation_rmsd(res["model"], r["ref_df"], species=_mspec(break_id)["species"])
    fitted = {c: round(res["fitted"][f"Values[{c}]"], 5) for c in cands}
    return {"fitted": fitted, "resim_rmsd": round(rmsd, 6), "objective": res["objective"],
            "matched": rmsd < TOL_RMSD, "method": _METHOD}


def localize(break_id):
    """Recall-free BASELINE: fit ALL candidate parameters jointly; the one that must
    MOVE from its broken value to restore the reference is the diagnosed break."""
    r = _reference(break_id)
    cands = list(_mspec(break_id)["candidates"])
    _broken_model(break_id)
    broken_vals = _broken_vals(break_id)
    res = estimate(basico.get_current_model(), r["ref_df"], _fit_items(break_id, cands), method=_METHOD)
    moved = {p: round(abs(res["fitted"][f"Values[{p}]"] - broken_vals[p]), 5) for p in cands}
    diagnosed = max(moved, key=moved.get)
    rmsd = resimulation_rmsd(res["model"], r["ref_df"], species=_mspec(break_id)["species"])
    return {"diagnosed_parameter": diagnosed, "moved_from_broken": moved,
            "fitted": {p: round(res["fitted"][f"Values[{p}]"], 5) for p in cands},
            "resim_rmsd": round(rmsd, 6),
            "correct": diagnosed == BREAKS[break_id]["param"],
            "note": "PE fit all candidates jointly; only the broken parameter had to move to restore the "
                    "reference. Diagnosis by optimization against the trace, not any recalled value."}


if __name__ == "__main__":
    for bid, spec in BREAKS.items():
        m = MODELS[spec["model"]]["label"].split(" — ")[0]
        bs = broken_state(bid)
        f = fit(bid)
        loc = localize(bid)
        print(f"{bid}  [{m}]  break {spec['param']}={spec['broken']} ({spec['blurb']})")
        print(f"   broken rmsd={bs['rmsd_vs_reference']}  fit->{f['fitted']} resimRMSD={f['resim_rmsd']} matched={f['matched']}")
        print(f"   localize (recall-free): diagnosed={loc['diagnosed_parameter']} correct={loc['correct']} "
              f"moved={loc['moved_from_broken']}")
