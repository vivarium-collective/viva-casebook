"""Head-to-head: the LLM-agent-driven build vs the deterministic-policy build.

Same study, same real process-bigraph composite, same locked tests — the only
difference is the DRIVER: an actual LLM reasoning over the margins vs a hand-coded
worst-negative-margin policy. Reads both captured trajectories and renders
docs/agent-vs-policy.html as a two-column comparison.
"""
import json
import os

HERE = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(HERE, os.pardir))
INV = os.path.join(ROOT, "workspace", "investigations", "model-building")
OUT = os.path.join(ROOT, "docs", "agent-vs-policy.html")
HARD = ["growth", "nutrient-depletion", "conservation", "viability-cliff", "viability-in-band"]


def _iter_common(label, n_pass, n_hard, edit, reasoning, newly, regressed, tests):
    return {"label": label, "n_pass": n_pass, "n_hard": n_hard, "edit": edit,
            "reasoning": reasoning, "newly_fixed": newly, "regressed": regressed,
            "tests": [{"name": t["name"], "verdict": t["verdict"], "margin": t["margin"]}
                      for t in tests if t["name"] in HARD]}


def norm_agent():
    t = json.load(open(os.path.join(INV, "agent_trajectory.json")))
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
    return {"driver": "LLM agent (Claude Sonnet)",
            "sub": "reasons each edit from the graded margins + a functional mechanism description",
            "edits": t["result"]["edits_to_pass"], "state": t["result"]["state"],
            "violations": len(t["result"]["violations"]), "calibrations": calib, "iters": iters}


def norm_policy():
    t = json.load(open(os.path.join(INV, "trajectory.json")))
    iters = []
    for it in t["iterations"]:
        d = it.get("decision")
        if not d:
            edit, reasoning = "DONE", "all hard tests pass → DONE"
        elif d["kind"] == "install":
            edit = "install: " + d["mechanism"]
            reasoning = "worst-negative-margin = " + d["test"] + " → install the mechanism it needs"
        elif d["kind"] == "calibrate":
            edit = "calibrate: t_tol → " + str(d.get("to"))
            reasoning = d["test"] + " still failing → step t_tol " + str(d.get("from")) + "→" + str(d.get("to")) + " (blind fixed step)"
        else:
            edit, reasoning = d["kind"], d.get("note", "")
        tests = [{"name": v["id"], "verdict": v["verdict"], "margin": v["margin"]} for v in it["verdicts"]]
        label = it.get("name") or (" + ".join(it.get("active", [])) or "inert draft")
        iters.append(_iter_common(label, it["n_pass"], it["n_hard"], edit, reasoning,
                     it["newly_fixed"], it["regressed"], tests))
    calib = sum(1 for it in t["iterations"] if (it.get("decision") or {}).get("kind") == "calibrate")
    return {"driver": "Deterministic policy",
            "sub": "a hand-coded rule: pick the worst-negative-margin hard test, install-or-calibrate",
            "edits": t["result"]["edits_to_pass"], "state": t["result"]["state"],
            "violations": len(t["result"]["violations"]), "calibrations": calib, "iters": iters}


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
  .foot{margin-top:44px;padding-top:16px;border-top:1px solid var(--line);font-size:12px;color:var(--soft);font-family:var(--mono)}
</style>
<div class="wrap">
  <div class="eyebrow">Same study · same composite · different driver</div>
  <h1>LLM agent vs deterministic policy</h1>
  <p class="lede">The exact same model-building study — same real process-bigraph composite, same locked tests, same mechanism library — built two ways. One driver is an actual LLM reasoning over the graded margins; the other is a hand-coded worst-negative-margin rule. Every verdict below is real engine output.</p>
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
const HARD=["growth","nutrient-depletion","conservation","viability-cliff","viability-in-band"];
const vc=(v)=>v==='within_tol'?['var(--good-w)','var(--good)']:v==='mismatch'?['var(--bad-w)','var(--bad)']:['var(--warn-w)','var(--warn)'];
const abbr={"growth":"grow","nutrient-depletion":"nutr","conservation":"cons","viability-cliff":"cliff","viability-in-band":"band"};

function scoreRow(label, a, p, awin){
  return `<tr><td class="metric">${label}</td><td class="${awin===true?'win':''}">${a}</td><td class="${awin===false?'win':''}">${p}</td></tr>`;
}
$('score').innerHTML=[
  scoreRow('Driver', A.driver, P.driver, null),
  scoreRow('Result', A.state, P.state, null),
  scoreRow('Edits to a passing model', A.edits, P.edits, A.edits<P.edits),
  scoreRow('Calibration steps for the tolerance', A.calibrations+' (computed t_tol in one shot)', P.calibrations+' (blind fixed steps)', A.calibrations<P.calibrations),
  scoreRow('Regressions caught & recovered', '2', '2', null),
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

$('insight').innerHTML='<b>Where they diverge.</b> Both drivers reach a passing, integrity-clean model, and both walk the same two real regressions (installing uptake breaks the mass balance until growth is added; the thermal mechanism\'s default tolerance breaks the in-band test until it is calibrated). The difference is the calibration: the deterministic policy steps the tolerance blindly ('+P.calibrations+' fixed steps) because it only knows the sign of the margin, while the LLM agent read the temperature ramp, computed that T(t=3h)≈41.9&nbsp;°C, and set <code>t_tol=43</code> in <b>one</b> step — reaching DONE in '+A.edits+' edits vs '+P.edits+'. The policy is faster and fully reproducible; the agent generalizes (it was never given the test→mechanism map) and reasons quantitatively. Same rails, same tests, same honest result — different kind of intelligence in the seat.';
$('foot').innerHTML='Agent decisions: real Claude Sonnet run via scripts/agent_step.py + capture_agent_run.py · policy: scripts/build_loop_demo.py · both on the same process-bigraph composite.';
</script>
"""


def main():
    html = (TEMPLATE.replace("__AGENT__", json.dumps(norm_agent()))
                    .replace("__POLICY__", json.dumps(norm_policy())))
    with open(OUT, "w") as fh:
        fh.write(html)
    print(f"rendered -> {os.path.relpath(OUT, ROOT)} ({len(html)} bytes)")


if __name__ == "__main__":
    main()
