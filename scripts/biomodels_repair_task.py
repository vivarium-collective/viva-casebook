"""Data-grounded task suite (Fable review #3): BioModels break-and-repair.

Loads a curated BioModels model (Elowitz 2000 repressilator) into the REAL COPASI
backend, simulates the REFERENCE behaviour, then BREAKS one kinetic parameter. The
agent is shown the parameter table + the divergence from reference, and must
diagnose which parameter is wrong and repair it so the model reproduces the
reference time-course.

The acceptance criterion is EXTERNAL ground truth — the intact reference model,
not an author-set band — so "repaired" means matching behaviour the model-builder
did not write. Scales to any BioModels entry / any break: a `BREAKS` registry
gives several well-posed breaks over different parameters, each a distinct
diagnostic problem.
"""
import os
import warnings

import numpy as np

warnings.filterwarnings("ignore")
import basico  # noqa: E402

MODEL = os.path.join(os.path.dirname(__file__), os.pardir, os.pardir,
                     "viva-copasi", "viva_copasi", "composites", "repressilator.xml")
_DURATION, _INTERVALS = 100.0, 100
_SPECIES = ["LacI protein", "TetR protein", "cI protein"]
TOL_RMSD = 0.15

# well-posed breaks (verified to shift the trace and repair cleanly). Each is a
# distinct diagnostic problem over a different biological parameter.
BREAKS = {
    "hill":        {"param": "n", "broken": 1.0,
                    "blurb": "the cooperative-repression Hill coefficient"},
    "km":          {"param": "KM", "broken": 80.0,
                    "blurb": "the repression half-saturation constant"},
    "translation": {"param": "translation efficiency", "broken": 10.0,
                    "blurb": "the translation efficiency (proteins per transcript)"},
}

_cache = {}   # break_id -> {ref, true}


def _load():
    basico.load_model(MODEL)


def _trace():
    tc = basico.run_time_course(duration=_DURATION, intervals=_INTERVALS)
    return {s: tc[s].to_numpy() for s in _SPECIES}


def _apply(param, value):
    basico.set_parameters(name=param, exact=True, initial_value=float(value))


def _reference(break_id):
    """Cache the intact reference trace + the reference parameter table + the true
    value of the break parameter. The displayed parameter table is tracked in
    Python (reference values + applied overrides) so it always reflects what was
    set — basico's get_parameters() value/initial_value semantics are unreliable
    across set_parameters, though the SIMULATION does honour the set."""
    if break_id not in _cache:
        _load()
        df = basico.get_parameters()
        ref_params = {n: round(float(df.loc[n, "value"]), 4) for n in df.index}
        spec = BREAKS[break_id]
        _cache[break_id] = {"ref": _trace(), "true": float(ref_params[spec["param"]]),
                            "ref_params": ref_params}
    return _cache[break_id]


def _rmsd(trace, ref):
    num = den = 0.0
    for s in _SPECIES:
        num += float(np.mean((trace[s] - ref[s]) ** 2))
        den += float(np.ptp(ref[s]) ** 2) or 1.0
    return float(np.sqrt(num / max(den, 1e-9)))


def _displayed_params(break_id, overrides=None):
    """Reference parameter table with the break (and any repair) applied — the
    view the agent sees."""
    r = _reference(break_id)
    tbl = dict(r["ref_params"])
    tbl[BREAKS[break_id]["param"]] = BREAKS[break_id]["broken"]
    for k, v in (overrides or {}).items():
        tbl[k] = round(float(v), 4)
    return tbl


def _broken_model(break_id):
    _load()
    _apply(BREAKS[break_id]["param"], BREAKS[break_id]["broken"])


def broken_state(break_id="hill"):
    r = _reference(break_id)
    _broken_model(break_id)
    return {"parameters": _displayed_params(break_id),
            "rmsd_vs_reference": round(_rmsd(_trace(), r["ref"]), 4),
            "note": "The model no longer reproduces its reference time-course. Diagnose which "
                    "parameter is wrong and repair it (set it to a value that restores the reference)."}


def repair(break_id, param, value):
    r = _reference(break_id)
    if param not in r["ref_params"]:
        return {"error": f"unknown parameter {param!r}", "available": sorted(r["ref_params"])}
    _broken_model(break_id)
    _apply(param, value)                       # real COPASI set → drives the simulation
    rmsd = _rmsd(_trace(), r["ref"])
    return {"param": param, "value": float(value), "rmsd_vs_reference": round(rmsd, 4),
            "matched": rmsd < TOL_RMSD}


if __name__ == "__main__":
    for bid, spec in BREAKS.items():
        r = _reference(bid)
        bs = broken_state(bid)
        good = repair(bid, spec["param"], r["true"])
        wrong = repair(bid, "beta", 1.0)   # a no-op parameter → should NOT repair
        print(f"{bid:12s} break {spec['param']}={spec['broken']} ({spec['blurb']}): "
              f"broken_rmsd={bs['rmsd_vs_reference']}  repair@true={good['rmsd_vs_reference']} "
              f"matched={good['matched']}  repair@wrong-param matched={wrong['matched']}")
