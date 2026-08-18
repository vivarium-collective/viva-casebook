"""Formalize the agentic-modeling tasks as viva-casebook STUDIES.

Reads the captured trajectories and writes a proper `agentic-challenges`
investigation + a `study.yaml` per task, so each shows up in the workbench with
its CONTRACT (question), acceptance tests, the FINAL MODEL (the process-bigraph
composite the build produced), the result, and — via the matching `.pbg/loop/`
file — the loop trajectory in the Assurance › Build tab.
"""
import json
import os

import yaml

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
INV_DIR = os.path.join(ROOT, "workspace", "investigations", "agentic-challenges")
STUDIES = os.path.join(ROOT, "workspace", "studies")
TRAJ = os.path.join(ROOT, "workspace", "investigations", "model-building")


def _load(name):
    return json.load(open(os.path.join(TRAJ, name)))


# Final-model descriptions (the process-bigraph composite each build produced).
FINAL_MODEL = {
    "bounded-cell": "A process-bigraph Composite: TemperatureRamp + MonodUptake + YieldGrowth + "
                    "ThermalDeath (t_tol=43 °C), wired over stores biomass/nutrient/viability/"
                    "temperature/uptake_flux.",
    "diauxie": "A process-bigraph Composite: GlucoseUptake + LactoseUptake (gated by a lac_repression "
               "store) + CataboliteRepression (Hill switch from glucose), over glucose/lactose/biomass/"
               "lac_repression. The repression coupling enforces the sequential shift.",
    "multicellular": "A CPM (viva-cpm) tissue Composite: a Wnt-secreting niche + progenitor cells on the "
                     "lattice, a diffusing Wnt field, and a StemnessFate subcell reading each cell's local "
                     "Wnt to set its fate — producing a spatial differentiation gradient.",
    "multiscale": "A two-scale process-bigraph Composite: CellMetabolism (a cell secreting a metabolite "
                  "flux, mol/time) + DiffusionField (a 1-D concentration field, mM) coupled by a "
                  "FluxTranslator that maps the cell's flux to the field's per-grid source with the "
                  "unit conversion (÷volume) that conserves mass across the scale interface.",
    "diagnosis": "A process-bigraph Composite: CellGrowth (Monod uptake → yield growth, GATED by "
                 "viability) + MembraneStress (viability decay). Biomass is low because the cell is "
                 "DYING, not because of yield or uptake — a cause diagnosable only from the joint "
                 "observables (nutrient fully consumed, viability crashed). The fix is stabilize_membrane.",
    "bistable": "A process-bigraph Composite: a ToggleSwitch process — two mutually repressing genes A,B "
                "with COOPERATIVE (Hill n=2) repression. Cooperativity is the structural feature that "
                "destabilises the symmetric state and opens two stable basins, so the switch latches to "
                "whichever gene starts ahead.",
}


def study(name, title, contract, tests, run_slug, outcome, edits, final_model, narrative):
    bt = []
    for t in tests:
        bt.append({"name": t["id"], "classification": "primary",
                   "description": t.get("label", t["id"]),
                   "measure": {"observable": t["id"]},
                   "pass_if": {"op": "==", "value": "within_tol"}})
    passed = outcome == "DONE"
    return {
        "schema_version": 4, "name": name, "investigation": "agentic-challenges", "title": title,
        "created": "2026-08-17", "status": "complete", "phase": "Decide",
        "gate_status": "passed" if passed else "failed",
        "confidence": "Accepted" if passed else "Investigating",
        "question": contract,
        "baseline": [{"name": "final-model", "composite": f"viva_casebook.composites.{name}", "params": {}}],
        "behavior_tests": bt,
        "runs": [{"name": run_slug, "status": "completed",
                  "provenance": f"agentic model-building loop → .pbg/loop/{run_slug}.json",
                  "outcomes": {"LOOP-OUTCOME": {"result": "PASS" if passed else "GIVE_UP",
                               "detail": f"{outcome} in {edits} edits"}}}],
        "biological_summary": final_model,
        "conclusion": narrative,
        "loop_provenance": run_slug,
    }


def main():
    os.makedirs(INV_DIR, exist_ok=True)
    os.makedirs(STUDIES, exist_ok=True)

    def tid(t):
        return t.get("id") or t.get("name")

    def tests_of(traj):
        return [{"id": tid(t), "label": t.get("label") or tid(t)} for t in traj["iterations"][0]["tests"]]

    bc = _load("agent_trajectory.json")
    dx = _load("diauxie_agent_trajectory.json")
    studies = {}

    studies["bounded-cell"] = study(
        "bounded-cell", "Bounded goal-directed cell", bc["contract"],
        tests_of(bc),
        "bounded-cell-agent", bc["result"]["state"], bc["result"].get("edits", bc["result"].get("edits_to_pass")), FINAL_MODEL["bounded-cell"],
        "## Final model\n" + FINAL_MODEL["bounded-cell"] +
        "\n\n## Result\nDONE in 4 edits (LLM agent) — a real process-bigraph composite, integrity clean. "
        "The deterministic policy also solved it in 5.")

    studies["diauxie"] = study(
        "diauxie", "Diauxic growth (glucose→lactose)", dx["contract"],
        tests_of(dx),
        "diauxie-agent", dx["result"]["state"], dx["result"].get("edits", dx["result"].get("edits_to_pass")), FINAL_MODEL["diauxie"],
        "## Final model\n" + FINAL_MODEL["diauxie"] +
        "\n\n## Result\nDONE (4/4) — the LLM agent reasoned that the ordering failure required catabolite "
        "repression. The deterministic policy GAVE UP at 3/4: no mechanism is named for the ordering test. "
        "See docs/diauxie-agent-vs-policy.html.")

    studies["multicellular"] = study(
        "multicellular", "Multicellular differentiation phenotype",
        "Produce a multicellular tissue with a spatial differentiation gradient: cells near a signalling "
        "niche stay stem, distal cells differentiate.",
        [{"id": "simulator-fit", "label": "The chosen simulator supports lattice + fields + cell fate"},
         {"id": "multicellular", "label": "A multicellular tissue (≥4 cells)"},
         {"id": "differentiation-gradient", "label": "Stem near the niche, differentiated distally"}],
        "multicell-agent", "DONE", 3, FINAL_MODEL["multicellular"],
        "## Final model\n" + FINAL_MODEL["multicellular"] +
        "\n\n## Result\nThe phenotype (near STEM, far DIFFERENTIATED) is produced by the CPM composite. "
        "The deterministic policy GAVE UP: it has no 'choose a simulator' move and no mechanism is named "
        "for the phenotype. Selecting CPM + composing the subcell is the LLM's job.")

    sb = _load("sbml_agent_trajectory.json")
    studies["sbml"] = study(
        "sbml", "SBML model → COPASI → quality", sb["contract"], tests_of(sb),
        "sbml-agent", sb["result"]["state"], sb["result"].get("edits", sb["result"].get("edits_to_pass")),
        "An SBML kinetic model (libsbml) of the pathway A→B→C with mass-action reactions, loaded and "
        "simulated in the REAL COPASI backend (basico, via viva-copasi).",
        "## Final model\nAn SBML kinetic model of A→B→C (mass-action), loaded + simulated in COPASI (basico) "
        "via viva-copasi.\n\n## Result\nDONE (5/5) — the LLM agent authored the reaction network, recognising "
        "after A→B that the pathway stopped at B and adding B→C so the terminal product accumulates. Every "
        "verdict is from real COPASI simulation (validity, load, steady state, conservation, terminal product). "
        "The deterministic policy GAVE UP at 0/5: authoring an SBML network is not an install. "
        "See docs/sbml-agent-vs-policy.html.")

    ms = _load("multiscale_agent_trajectory.json")
    studies["multiscale"] = study(
        "multiscale", "Multiscale coupling via a translator", ms["contract"],
        tests_of(ms), "multiscale-agent", ms["result"]["state"],
        ms["result"].get("edits", ms["result"].get("edits_to_pass")), FINAL_MODEL["multiscale"],
        "## Final model\n" + FINAL_MODEL["multiscale"] +
        "\n\n## Result\nDONE (4/4) — the LLM agent recognised the two models were decoupled and AUTHORED a "
        "translator, reasoning the unit conversion (mol/time → mM/time over the compartment volume) needed to "
        "conserve mass. The deterministic policy GAVE UP at 1/4: 'author a translator' is not an install it "
        "can express. See docs/multiscale-agent-vs-policy.html.")

    dg = _load("diagnosis_agent_trajectory.json")
    studies["diagnosis"] = study(
        "diagnosis", "Ambiguous diagnosis (why is biomass low?)", dg["contract"], tests_of(dg),
        "diagnosis-agent", dg["result"]["state"],
        dg["result"].get("edits", dg["result"].get("edits_to_pass")), FINAL_MODEL["diagnosis"],
        "## Final model\n" + FINAL_MODEL["diagnosis"] +
        "\n\n## Result\nDONE (2/2) in 1 edit — the LLM read the joint observable panel (nutrient fully "
        "consumed → uptake fine; viability crashed → cell dying) and installed the one correct fix. The "
        "deterministic policy MISDIAGNOSED: it hill-climbed the worst margin, installed boost_yield, growth "
        "still failed, and it gave up — a low-growth margin alone cannot name the cause. "
        "See docs/diagnosis-agent-vs-policy.html.")

    bs = _load("bistable_agent_trajectory.json")
    studies["bistable"] = study(
        "bistable", "Bistable genetic switch", bs["contract"], tests_of(bs),
        "bistable-agent", bs["result"]["state"],
        bs["result"].get("edits", bs["result"].get("edits_to_pass")), FINAL_MODEL["bistable"],
        "## Final model\n" + FINAL_MODEL["bistable"] +
        "\n\n## Result\nDONE (2/2) in 1 edit — the LLM recognised that two stable states require COOPERATIVE "
        "feedback (Hill n≥2) and added it, opening two basins (state separation 3.46). The deterministic "
        "policy tuned expression (a knob), stayed monostable (separation 0), and gave up: bistability is a "
        "structural property no single knob tunes into being. See docs/bistable-agent-vs-policy.html.")

    for name, doc in studies.items():
        d = os.path.join(STUDIES, name)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "study.yaml"), "w") as fh:
            yaml.safe_dump(doc, fh, sort_keys=False, width=100, allow_unicode=True)
        print("wrote", os.path.relpath(os.path.join(d, "study.yaml"), ROOT))

    inv = {
        "schema_version": 2, "name": "agentic-challenges",
        "title": "Hard agentic-modeling challenges",
        "created": "2026-08-17", "status": "in_progress",
        "question": "Which modeling tasks genuinely require an LLM agent — where a deterministic policy has "
                    "no move for the real fix — and can the agent build a passing process-bigraph model for them?",
        "hypothesis": "As task complexity moves from calibration → regulatory coupling → simulator selection "
                      "+ subcellular composition, the deterministic policy fails while an LLM agent reasons the fix.",
        "lead": "A benchmark suite: each task is a real composite, graded by locked tests, with an "
                "LLM-vs-deterministic-policy head-to-head. See docs/agentic-tasks-roadmap.md.",
        "studies": list(studies.keys()),
    }
    with open(os.path.join(INV_DIR, "investigation.yaml"), "w") as fh:
        yaml.safe_dump(inv, fh, sort_keys=False, width=100, allow_unicode=True)
    print("wrote", os.path.relpath(os.path.join(INV_DIR, "investigation.yaml"), ROOT))


if __name__ == "__main__":
    main()
