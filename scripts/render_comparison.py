"""Head-to-head: the LLM-agent-driven build vs the deterministic-policy build.

Same study, same real process-bigraph composite, same locked tests — the only
difference is the DRIVER: an actual LLM reasoning over the margins vs a hand-coded
worst-negative-margin policy. Reads both captured trajectories and renders
docs/agent-vs-policy.html as a two-column comparison.
"""
import argparse
import json
import os

HERE = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(HERE, os.pardir))
INV = os.path.join(ROOT, "workspace", "investigations", "model-building")
# defaults render the bounded-cell pair; override via CLI for other studies.
HARD = ["growth", "nutrient-depletion", "conservation", "viability-cliff", "viability-in-band"]


def _abbr(name):
    """A short (≤6-char) strip label for a test id, derived generically."""
    parts = str(name).replace("_", "-").split("-")
    if len(parts) >= 2:
        return (parts[0][:4] + parts[-1][:2]).lower()
    return str(name)[:6].lower()


def _iter_common(label, n_pass, n_hard, edit, reasoning, newly, regressed, tests):
    def nm(t):
        return t.get("name") or t.get("id")
    return {"label": label, "n_pass": n_pass, "n_hard": n_hard, "edit": edit,
            "reasoning": reasoning, "newly_fixed": newly, "regressed": regressed,
            "tests": [{"name": nm(t), "verdict": t["verdict"], "margin": t["margin"]}
                      for t in tests if nm(t) in HARD]}


def norm_agent(path):
    t = json.load(open(path))
    iters = []
    for it in t["iterations"]:
        d = it["agent_decision"]
        edit = ("DONE" if d["action"] == "done"
                else d["action"] + ": " + (d.get("mechanism") or d.get("knob") or ""))
        if d["action"] == "calibrate":
            edit += " → " + str(d.get("value"))
        iters.append(_iter_common(" + ".join(it["active"]) or "inert draft",
                     it["n_pass"], it["n_hard"], edit, d.get("reasoning", ""),
                     it["newly_fixed"], it["regressed"], it["tests"]))
    calib = sum(1 for it in t["iterations"] if it["agent_decision"].get("action") == "calibrate")
    prov = t.get("provenance", "illustrative")
    # honour the trajectory's own driver string (live runs carry "LIVE (model), n=..");
    # only fall back to a generic label for older hardcoded trajectories.
    driver = t.get("driver") or "LLM agent (Claude Sonnet)"
    return {"driver": driver if prov == "live" else "LLM agent (Claude Sonnet)",
            "driver_full": driver, "provenance": prov, "n_runs": t.get("n_runs"),
            "pass_rate": t.get("pass_rate"),
            "sub": "reasons each edit from the graded margins + a functional mechanism description",
            "edits": t["result"].get("edits_to_pass", t["result"].get("edits")), "state": t["result"]["state"],
            "violations": len(t["result"].get("violations", [])), "calibrations": calib, "iters": iters}


def norm_policy(path):
    t = json.load(open(path))
    iters = []
    for it in t["iterations"]:
        d = it.get("decision")
        if not d:
            edit, reasoning = "DONE", "all hard tests pass → DONE"
        elif d["kind"] == "install":
            edit = "install: " + d["mechanism"]
            reasoning = "worst-negative-margin = " + str(d.get("test") or d.get("for_test")) + " → install the mechanism it needs"
        elif d["kind"] == "calibrate":
            edit = "calibrate: t_tol → " + str(d.get("to"))
            reasoning = d["test"] + " still failing → step t_tol " + str(d.get("from")) + "→" + str(d.get("to")) + " (blind fixed step)"
        else:
            edit, reasoning = d["kind"], d.get("note", "")
        tests = [{"name": v.get("id") or v.get("name"), "verdict": v["verdict"], "margin": v["margin"]}
                 for v in (it.get("verdicts") or it.get("tests") or [])]
        label = it.get("name") or (" + ".join(it.get("active", [])) or "inert draft")
        iters.append(_iter_common(label, it["n_pass"], it["n_hard"], edit, reasoning,
                     it["newly_fixed"], it["regressed"], tests))
    calib = sum(1 for it in t["iterations"] if (it.get("decision") or {}).get("kind") == "calibrate")
    return {"driver": "Deterministic policy",
            "sub": "a hand-coded rule: pick the worst-negative-margin hard test, install-or-calibrate",
            "edits": t["result"].get("edits_to_pass", t["result"].get("edits")), "state": t["result"]["state"],
            "violations": len(t["result"].get("violations", [])), "calibrations": calib, "iters": iters}


TEMPLATE = r"""<title>Agent vs Policy</title>
<style>
  :root{--ground:#f5f8f7;--panel:#fff;--panel2:#fbfdfc;--ink:#0c1a19;--soft:#4a5b59;--line:#e2e9e7;--line2:#c9d4d1;
    --teal:#0d9488;--teal-deep:#0f766e;--wash:#e6f4f1;--good:#059669;--good-w:#e7f4ee;--warn:#b45309;--warn-w:#fbf1e3;--bad:#dc2626;--bad-w:#fbeaea;
    --violet:#7c3aed;--violet-w:#f1ebfd;--mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;--sans:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;}
  @media(prefers-color-scheme:dark){:root:not([data-theme=light]){--ground:#0b1211;--panel:#111b1a;--panel2:#0e1716;--ink:#e8f0ee;--soft:#93a5a2;--line:#1e2b29;--line2:#2c3d3a;
    --teal:#2dd4bf;--teal-deep:#5eead4;--wash:#0f2320;--good:#34d399;--good-w:#0e241c;--warn:#fbbf24;--warn-w:#241a08;--bad:#f87171;--bad-w:#2a1414;--violet:#a78bfa;--violet-w:#1c1633;}}
  :root[data-theme=dark]{--ground:#0b1211;--panel:#111b1a;--panel2:#0e1716;--ink:#e8f0ee;--soft:#93a5a2;--line:#1e2b29;--line2:#2c3d3a;
    --teal:#2dd4bf;--teal-deep:#5eead4;--wash:#0f2320;--good:#34d399;--good-w:#0e241c;--warn:#fbbf24;--warn-w:#241a08;--bad:#f87171;--bad-w:#2a1414;--violet:#a78bfa;--violet-w:#1c1633;}
  *{box-sizing:border-box}body{margin:0;background:var(--ground);color:var(--ink);font-family:var(--sans);line-height:1.55;-webkit-font-smoothing:antialiased}
  .wrap{max-width:1000px;margin:0 auto;padding:44px 22px 90px}
  .eyebrow{font-family:var(--mono);font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:var(--teal-deep);font-weight:600}
  h1{font-size:clamp(28px,4.4vw,42px);line-height:1.06;margin:10px 0 8px;letter-spacing:-.02em}
  .lede{font-size:17px;color:var(--soft);max-width:70ch;margin:0}
  h2{font-size:13px;font-family:var(--mono);letter-spacing:.1em;text-transform:uppercase;color:var(--soft);font-weight:600;margin:44px 0 14px;padding-bottom:8px;border-bottom:1px solid var(--line)}
  .score{overflow-x:auto;border:1px solid var(--line);border-radius:12px;background:var(--panel)}
  table{border-collapse:collapse;width:100%;font-size:14px}th,td{padding:11px 14px;border-bottom:1px solid var(--line);text-align:left}
  th{font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--soft);font-weight:600;background:var(--wash)}
  tbody tr:last-child td{border-bottom:none}.metric{font-weight:600}.win{color:var(--good);font-weight:700}
  .cols{display:grid;grid-template-columns:1fr 1fr;gap:16px}@media(max-width:760px){.cols{grid-template-columns:1fr}}
  .col{border:1px solid var(--line);border-radius:14px;background:var(--panel);overflow:hidden}
  .col-h{padding:14px 16px;border-bottom:1px solid var(--line)}
  .col-h .d{font-weight:700;font-size:15px;display:flex;align-items:center;gap:8px}
  .col-h .s{font-size:12px;color:var(--soft);margin-top:3px}
  .badge{font-family:var(--mono);font-size:10px;font-weight:700;padding:2px 8px;border-radius:999px}
  .b-agent{background:var(--violet-w);color:var(--violet)} .b-policy{background:var(--wash);color:var(--teal-deep)}
  .col-b{padding:12px 14px}
  .it{border:1px solid var(--line);border-radius:10px;margin-bottom:9px;overflow:hidden}
  .it.done{border-color:var(--good)}
  .it-h{display:flex;align-items:center;gap:8px;padding:8px 11px;background:var(--panel2);border-bottom:1px solid var(--line);font-size:12px}
  .it-h .k{font-family:var(--mono);font-weight:700;color:var(--teal-deep)}
  .it-h .lbl{font-family:var(--mono);color:var(--soft);font-size:11px}
  .it-h .sc{margin-left:auto;font-family:var(--mono);font-weight:700}
  .strip{display:flex;gap:3px;padding:8px 11px 4px}
  .cell{flex:1;height:20px;border-radius:3px;display:flex;align-items:center;justify-content:center;font-family:var(--mono);font-size:9px;font-weight:700}
  .it-e{padding:2px 11px 10px;font-size:12px}
  .it-e .edit{font-family:var(--mono);font-weight:600}
  .it-e .rz{color:var(--soft);font-size:11.5px;margin-top:3px;font-style:italic}
  .tag{font-family:var(--mono);font-size:9.5px;font-weight:700;padding:1px 5px;border-radius:4px;margin-left:5px}
  .t-fx{background:var(--good-w);color:var(--good)} .t-rg{background:var(--bad-w);color:var(--bad)}
  .callout{border:1px solid var(--line2);border-left:3px solid var(--violet);border-radius:10px;padding:14px 16px;background:var(--panel);margin-top:16px;font-size:13.5px;color:var(--soft)}
  .callout b{color:var(--ink)}
  .prov{margin-top:14px;font-size:12.5px;font-family:var(--mono);display:inline-flex;gap:8px;align-items:center;padding:6px 12px;border-radius:999px;border:1px solid var(--line2)}
  .prov.live{background:var(--good-w);color:var(--good)} .prov.illustrative{background:var(--warn-w);color:var(--warn)}
  .foot{margin-top:44px;padding-top:16px;border-top:1px solid var(--line);font-size:12px;color:var(--soft);font-family:var(--mono)}
</style>
<div class="wrap">
  <div class="eyebrow">Same study · same composite · different driver</div>
  <h1>__TITLE__</h1>
  <p class="lede">The exact same model-building study — same real process-bigraph composite, same locked tests, same mechanism library — built two ways. One driver is an actual LLM reasoning over the graded margins; the other is a hand-coded worst-negative-margin rule. Every verdict below is real engine output.</p>
  <div class="prov" id="prov"></div>
  <h2>Scorecard</h2>
  <div class="score"><table><thead><tr><th>Metric</th><th>🤖 LLM agent</th><th>⚙️ Deterministic policy</th></tr></thead><tbody id="score"></tbody></table></div>
  <h2>The two builds, side by side</h2>
  <div class="cols"><div class="col" id="col-agent"></div><div class="col" id="col-policy"></div></div>
  <div class="callout" id="insight"></div>
  <div class="foot" id="foot"></div>
</div>
<script>
const A=__AGENT__, P=__POLICY__;
const $=(id)=>document.getElementById(id);
const HARD=__HARD__;
const vc=(v)=>v==='within_tol'?['var(--good-w)','var(--good)']:v==='mismatch'?['var(--bad-w)','var(--bad)']:['var(--warn-w)','var(--warn)'];
const abbr=__ABBR__;

function scoreRow(label, a, p, awin){
  return `<tr><td class="metric">${label}</td><td class="${awin===true?'win':''}">${a}</td><td class="${awin===false?'win':''}">${p}</td></tr>`;
}
// count regressions actually observed in each trajectory (no hardcoding)
function regCount(run){ return (run.iters||[]).reduce(function(n,it){ return n+((it.regressed||[]).length); },0); }
$('score').innerHTML=[
  scoreRow('Driver', A.driver, P.driver, null),
  scoreRow('Result', A.state, P.state, null),
  scoreRow('Edits to a passing model', A.edits, P.edits, A.edits<P.edits),
  scoreRow('Calibration steps for the tolerance', A.calibrations, P.calibrations, A.calibrations<P.calibrations),
  scoreRow('Regressions observed', regCount(A), regCount(P), null),
  scoreRow('Integrity violations', A.violations, P.violations, null),
].join("");

function renderCol(run, cls, badge){
  var h='<div class="col-h"><div class="d">'+(cls==='agent'?'🤖':'⚙️')+' '+run.driver+' <span class="badge b-'+cls+'">'+badge+'</span></div><div class="s">'+run.sub+'</div></div><div class="col-b">';
  run.iters.forEach(function(it){
    var done=it.edit==='DONE';
    var strip=HARD.map(function(nm){var t=it.tests.filter(function(x){return x.name===nm;})[0];var c=t?vc(t.verdict):['var(--panel2)','var(--soft)'];
      return '<div class="cell" style="background:'+c[0]+';color:'+c[1]+'" title="'+nm+'">'+(abbr[nm]||nm)+'</div>';}).join("");
    var tags=it.newly_fixed.map(function(x){return '<span class="tag t-fx">+'+(abbr[x]||x)+'</span>';}).join("")
            +it.regressed.map(function(x){return '<span class="tag t-rg">−'+(abbr[x]||x)+'</span>';}).join("");
    h+='<div class="it '+(done?'done':'')+'"><div class="it-h"><span class="k">i'+run.iters.indexOf(it)+'</span>'
      +'<span class="lbl">'+(it.label||'')+'</span><span class="sc">'+it.n_pass+'/'+it.n_hard+'</span></div>'
      +'<div class="strip">'+strip+'</div>'
      +'<div class="it-e"><span class="edit">'+it.edit+'</span>'+tags
      +(it.reasoning&&!done?'<div class="rz">"'+it.reasoning+'"</div>':'')+'</div></div>';
  });
  return h+'</div>';
}
$('col-agent').innerHTML=renderCol(A,'agent','reasoned');
$('col-policy').innerHTML=renderCol(P,'policy','coded');

$('insight').innerHTML=__INSIGHT__;

// provenance banner: honest about whether the agent column is a LIVE run or an illustrative transcript
(function(){
  var live = A.provenance==='live';
  var p=$('prov'); p.className='prov '+(live?'live':'illustrative');
  if(live){
    p.innerHTML='● LIVE agent run · '+(A.driver_full||A.driver)+(A.pass_rate!=null?(' · pass-rate '+A.pass_rate):'')
      +' · single-trajectory demonstration (n='+(A.n_runs||1)+')';
  } else {
    p.innerHTML='◐ Illustrative hand-authored transcript — not a live model run; a worked example of the comparison format';
  }
})();
$('foot').innerHTML=__FOOT__;
</script>
"""


CALIBRATION_INSIGHT = (
    "'<b>Where they diverge.</b> Both drivers reach a passing, integrity-clean model, and both walk the "
    "same two real regressions. The difference is the calibration: the deterministic policy steps the "
    "tolerance blindly ('+P.calibrations+' fixed steps) because it only knows the sign of the margin, while "
    "the LLM-agent column resolves the tolerance in a <b>single</b> reasoned step — DONE in '+A.edits+' "
    "edits vs '+P.edits+'. <i>Note: this page is an illustrative hand-authored transcript, not a live model "
    "run — a worked example of the comparison format. The reasoned calibration is a stand-in for the kind "
    "of one-shot move an agent makes when it can reason about the dynamics; the environment here does not "
    "expose the underlying ramp, so treat it as illustrative, not as measured live behaviour.</i>'")

GIVEUP_INSIGHT = (
    "'<b>The task the policy could not do.</b> The deterministic policy consumed both substrates and grew, "
    "but got the <b>regulation</b> wrong — it ate lactose at the same time as glucose — and then <b>gave up</b> "
    "('+P.iters[P.iters.length-1].n_pass+'/'+P.iters[P.iters.length-1].n_hard+'), because no mechanism is "
    "<i>named</i> for the ordering test and its worst-margin rule had no move. The LLM agent, on the identical "
    "task, reasoned that lactose was being co-consumed because <code>lac_repression</code> was stuck ON, and "
    "installed <b>catabolite repression</b> to gate lactose uptake by glucose — reaching DONE in '+A.edits+' "
    "edits. This is the difference a real task exposes: the fix was not a knob and not a name-matched "
    "mechanism, it was a <b>regulatory coupling</b> that had to be reasoned from the biology.'")

# diagnosis (live): the binding constraint was on an observable the metric didn't name.
DIAGNOSIS_INSIGHT = (
    "'<b>Reading the right observable.</b> Biomass was far below target, so the obvious lever is yield — "
    "and the deterministic policy, keyed to the biomass margin, installs <code>boost_yield</code>. But "
    "yield did nothing: <code>viability_final</code> was <b>0</b> — the cell was dying mid-run, capping "
    "biomass regardless of yield. The LLM agent read the <i>joint</i> observable panel, saw nutrient fully "
    "consumed yet viability collapsed, inferred the binding constraint was membrane viability rather than "
    "yield, and switched to <code>stabilize_membrane</code> — DONE in '+A.edits+' edits. The fix required "
    "diagnosing <i>which</i> observable was actually limiting, not optimizing the one the goal named.'")

# bistable (live): the fix is a change in the FORM of the interaction, not a rate.
BISTABLE_INSIGHT = (
    "'<b>Structure, not rate.</b> Two mutually repressing genes only become <b>bistable</b> when the "
    "repression is <i>cooperative</i> (Hill n≥2) — that is what carves two stable basins with a saddle "
    "between them. The deterministic policy can raise expression or degradation, but both merely scale "
    "rates and never create a second stable state, so it cannot reach the target. The LLM agent reasoned "
    "from the biology (cf. Gardner et&nbsp;al. 2000) that the missing ingredient was cooperativity, and "
    "installed <code>cooperative_binding</code> — reaching DONE in '+A.edits+' edits. The decisive move "
    "changed the <b>form</b> of the interaction, which no single-knob rule reaches.'")

# multicell (illustrative): an emergent tissue-scale phenotype + a simulator-selection move.
MULTICELL_INSIGHT = (
    "'<b>A tissue-scale phenotype, chosen not tuned.</b> The target — a spatial differentiation gradient "
    "where cells near a niche stay stem and distant cells differentiate — is a <i>tissue-scale</i> "
    "property no single-cell knob produces. The decisive moves were structural: SELECT the one simulator "
    "(CPM) whose substrate supports a lattice + morphogen field + cell-fate relabeling, add the Wnt niche "
    "field, then a subcellular fate model that reads local Wnt to relabel cells — DONE in '+A.edits+' "
    "edits. A worst-margin knob rule has nothing to turn here.'")

# multiscale (illustrative): the fix is an authored cross-scale translator with a unit conversion.
MULTISCALE_INSIGHT = (
    "'<b>The fix was a cross-scale translator, authored.</b> Coupling a cell-scale metabolic FLUX to a "
    "tissue-scale DIFFUSION field means the two models stay unconnected until something maps "
    "<code>secretion_flux → field_source</code>. And the units differ — mol/time vs mM/time over volume "
    "V=2.0 — so mass only conserves across the interface if the conversion is applied. The agent authored "
    "that translator; DONE in '+A.edits+' edits. This is not a menu mechanism — it is a unit-correct "
    "coupling that has to be reasoned from the two scales.'")

# sbml (illustrative): a whole-model validity property that turns on pathway topology.
SBML_INSIGHT = (
    "'<b>Whole-model validity, from topology.</b> The target is not a number but a set of model-validity "
    "properties: COPASI loads the SBML, it reaches a <i>valid</i> steady state, mass is conserved, and the "
    "terminal product C is the dominant species. The agent reasoned about the pathway TOPOLOGY — A→B alone "
    "leaves B terminal, so C never accumulates; adding B→C makes C the sink — DONE in '+A.edits+' edits. "
    "The move was structural (which reactions exist), not a rate the policy could step.'")

_INSIGHTS = {"calibration": CALIBRATION_INSIGHT, "giveup": GIVEUP_INSIGHT,
             "diagnosis": DIAGNOSIS_INSIGHT, "bistable": BISTABLE_INSIGHT,
             "multicell": MULTICELL_INSIGHT, "multiscale": MULTISCALE_INSIGHT, "sbml": SBML_INSIGHT}

_FOOT_LIVE = ("'Agent column: LIVE Claude run (single trajectory, n=1) via scripts/run_agent.py → "
              "scripts/live_to_trajectory.py — integrity violations computed from a real loop_state "
              "replay. Policy: scripts/build_loop_demo.py. Both on the same process-bigraph composite. "
              "For the full n≥5 pass-rate distribution, run scripts/run_agent.py with an API key.'")
_FOOT_ILLUS = ("'Agent column: illustrative hand-authored transcript (scripts/capture_*.py) — a worked "
               "example of the comparison format, not a live model run. Policy: scripts/build_loop_demo.py. "
               "Both on the same process-bigraph composite.'")


def main():
    global HARD
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", default=os.path.join(INV, "agent_trajectory.json"))
    ap.add_argument("--policy", default=os.path.join(INV, "trajectory.json"))
    ap.add_argument("--hard", default=",".join(HARD))
    ap.add_argument("--out", default=os.path.join(ROOT, "docs", "agent-vs-policy.html"))
    ap.add_argument("--title", default="LLM agent vs deterministic policy")
    ap.add_argument("--insight", choices=sorted(_INSIGHTS), default="calibration")
    args = ap.parse_args()
    # HARD = the test ids shown in the per-iteration strip. Derive from the agent
    # trajectory unless overridden, so every task (not just bounded-cell) renders.
    if args.hard and args.hard != ",".join(["growth", "nutrient-depletion", "conservation",
                                            "viability-cliff", "viability-in-band"]):
        HARD = args.hard.split(",")
    else:
        at = json.load(open(args.agent))
        ids = []
        for t in at.get("tests", []):
            tid = t.get("id") or t.get("name")
            if tid and tid not in ids:
                ids.append(tid)
        HARD = ids or args.hard.split(",")
    abbr = {h: _abbr(h) for h in HARD}
    agent = norm_agent(args.agent)
    foot = _FOOT_LIVE if agent.get("provenance") == "live" else _FOOT_ILLUS
    html = (TEMPLATE.replace("__AGENT__", json.dumps(agent))
                    .replace("__POLICY__", json.dumps(norm_policy(args.policy)))
                    .replace("__TITLE__", args.title)
                    .replace("__INSIGHT__", _INSIGHTS[args.insight])
                    .replace("__HARD__", json.dumps(HARD))
                    .replace("__ABBR__", json.dumps(abbr))
                    .replace("__FOOT__", foot))
    with open(args.out, "w") as fh:
        fh.write(html)
    print(f"rendered -> {os.path.relpath(args.out, ROOT)} ({len(html)} bytes, "
          f"provenance={agent.get('provenance')})")


if __name__ == "__main__":
    main()
