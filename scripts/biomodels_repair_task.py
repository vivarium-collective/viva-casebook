"""Data-grounded task (Fable review #3): BioModels break-and-repair.

Loads a curated BioModels model (Elowitz 2000 repressilator) into the REAL COPASI
backend, simulates the REFERENCE behavior, then BREAKS one kinetic parameter. The
agent is shown the parameter table and the divergence from reference, and must
diagnose which parameter is wrong and repair it so the model reproduces the
reference time-course.

Unlike the toy tasks, the acceptance criterion is not an author-set band: the
ground truth IS the intact reference model, so "repaired" means the model matches
behavior the model-builder did not write. Objective, and scalable to any
BioModels entry / any break.
"""
import os
import warnings

import numpy as np

warnings.filterwarnings("ignore")
import basico  # noqa: E402

MODEL = os.path.join(os.path.dirname(__file__), os.pardir, os.pardir,
                     "viva-copasi", "viva_copasi", "composites", "repressilator.xml")
_DURATION, _INTERVALS = 100.0, 100
# the deliberately-broken parameter (Hill coefficient of the cooperative repression)
BREAK_PARAM = "n"
BROKEN_VALUE = 1.0          # true value is ~2 (cooperative); 1 kills the oscillation
TOL_RMSD = 0.15             # fraction-of-reference-amplitude RMSD to count as repaired
_SPECIES = ["LacI protein", "TetR protein", "cI protein"]

_ref = None
_true = None


def _load():
    basico.load_model(MODEL)


def _trace():
    tc = basico.run_time_course(duration=_DURATION, intervals=_INTERVALS)
    return {s: tc[s].to_numpy() for s in _SPECIES}


def _reference():
    """Intact-model reference trace + the true value of the broken parameter."""
    global _ref, _true
    if _ref is None:
        _load()
        _true = float(basico.get_parameters(name=BREAK_PARAM).loc[BREAK_PARAM, "value"])
        _ref = _trace()
    return _ref, _true


def _rmsd(trace):
    ref, _ = _reference()
    num = 0.0
    den = 0.0
    for s in _SPECIES:
        a, b = trace[s], ref[s]
        num += float(np.mean((a - b) ** 2))
        den += float(np.ptp(b) ** 2) or 1.0          # normalize by reference amplitude²
    return float(np.sqrt(num / max(den, 1e-9)))


def parameters():
    """Global parameters (name → current value) — the agent's diagnostic view."""
    _reference()
    df = basico.get_parameters()
    return {n: round(float(df.loc[n, "value"]), 4) for n in df.index}


def _apply(param, value):
    basico.set_parameters(name=param, exact=True, initial_value=float(value))


def broken_state():
    """Load the model with BREAK_PARAM set to BROKEN_VALUE; return the divergence."""
    _reference()
    _load()
    _apply(BREAK_PARAM, BROKEN_VALUE)
    br = _trace()
    return {"parameters": parameters(), "rmsd_vs_reference": round(_rmsd(br), 4),
            "note": "The model no longer reproduces its reference time-course. Diagnose which "
                    "parameter is wrong and repair it (set it to a value that restores the reference)."}


def repair(param, value):
    """Set `param`=`value` on the broken model; grade against the reference."""
    _reference()
    _load()
    _apply(BREAK_PARAM, BROKEN_VALUE)          # start from the broken model
    if param not in parameters():
        return {"error": f"unknown parameter {param!r}", "available": sorted(parameters())}
    _apply(param, value)
    r = _rmsd(_trace())
    return {"param": param, "value": float(value), "rmsd_vs_reference": round(r, 4),
            "matched": r < TOL_RMSD}


if __name__ == "__main__":
    ref, true = _reference()
    print(f"reference loaded; true {BREAK_PARAM} = {true:.4f}")
    bs = broken_state()
    print(f"broken ({BREAK_PARAM}={BROKEN_VALUE}): rmsd_vs_reference = {bs['rmsd_vs_reference']}")
    for cand, val in [("alpha", 100), (BREAK_PARAM, BROKEN_VALUE), (BREAK_PARAM, true)]:
        r = repair(cand, val)
        print(f"repair {cand}={val}: rmsd={r['rmsd_vs_reference']} matched={r['matched']}")
