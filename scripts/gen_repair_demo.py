"""Regenerate the break-and-repair evidence on the COPASI parameter-estimation
substrate (Fable re-review #2). Deterministic — no LLM recall; every number is
real COPASI PE output. Writes workspace/.../repair_suite_live.json.

Replaces the earlier artifact whose recorded diagnoses reasoned from memorized
canonical values ("KM=80 is double the canonical 40"). Here the diagnosis is by
OPTIMIZATION: PE fits the reference trace and recovers the true value; the
`localize` baseline fits all candidates and identifies the broken one by which
must move — no canonical value consulted.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import biomodels_repair_task as R  # noqa: E402

OUT = os.path.join(os.path.dirname(__file__), os.pardir, "workspace", "investigations", "model-building")


def main():
    runs = []
    for bid, spec in R.BREAKS.items():
        true = R._reference(bid)["true_params"][spec["param"]]
        bs = R.broken_state(bid)
        f = R.fit(bid)
        loc = R.localize(bid)
        runs.append({
            "break_id": bid, "param": spec["param"], "blurb": spec["blurb"],
            "broken_value": spec["broken"], "true_value": true,
            "broken_rmsd": bs["rmsd_vs_reference"],
            "fit": {"fitted": f["fitted"], "resim_rmsd": f["resim_rmsd"], "matched": f["matched"],
                    "method": f["method"]},
            "localize": {"diagnosed_parameter": loc["diagnosed_parameter"], "correct": loc["correct"],
                         "moved_from_broken": loc["moved_from_broken"]},
        })
    doc = {
        "schema": "repair_suite_pe/v1",
        "task": "break-and-repair via COPASI parameter estimation",
        "model": "repressilator (SBML) simulated in the real COPASI backend",
        "oracle": "COPASI Parameter Estimation (Levenberg–Marquardt) fitting the intact reference "
                  "time-course — recall-free by construction; the optimizer never sees a canonical value",
        "driver": "deterministic demonstration of the PE repair + recall-free localization machinery — "
                  "no LLM recall; every value is real COPASI PE output (reproduce: "
                  "python scripts/gen_repair_demo.py)",
        "candidate_parameters": list(R._CANDIDATES),
        "runs": runs,
        "summary": {
            "n_breaks": len(runs),
            "all_repaired": all(r["fit"]["matched"] for r in runs),
            "all_localized_correctly": all(r["localize"]["correct"] for r in runs),
            "note": "Each break is repaired by optimization (PE recovers the true value, resim RMSD ~0) and "
                    "independently DIAGNOSED by the recall-free localization baseline (fit all candidates; "
                    "the broken one is the one that must move). Break ids are opaque; the reference and "
                    "broken time-courses are shown on the card. Celebrity-ness of the model no longer "
                    "helps — the oracle is an optimizer, not recall.",
        },
    }
    path = os.path.join(OUT, "repair_suite_live.json")
    json.dump(doc, open(path, "w"), indent=2)
    for r in runs:
        print(f"{r['break_id']}: fit {r['param']}->{r['fit']['fitted']} matched={r['fit']['matched']} | "
              f"localize diagnosed={r['localize']['diagnosed_parameter']} correct={r['localize']['correct']}")
    print("wrote", os.path.relpath(path))


if __name__ == "__main__":
    main()
