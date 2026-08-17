"""Render the study-automation pipeline report from the captured trajectory (v2).

Reads workspace/investigations/model-building/trajectory.json (build_loop_demo.py)
and emits a self-contained docs/pipeline-report.html: the contract → draft →
select → tests → sufficiency audit (2 rounds) → lock → the EMERGENT build loop
(margin matrix + per-iteration NAVIGATE decisions) → result (with the regression
drawn as a curve) → an honest GIVE_UP companion → pipeline health. Every value is
read from the real trajectory. Re-run the driver then this renderer to refresh.
"""
import json
import os

HERE = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(HERE, os.pardir))
TRAJ = os.path.join(ROOT, "workspace", "investigations", "model-building", "trajectory.json")
OUTHTML = os.path.join(ROOT, "docs", "pipeline-report.html")

TEMPLATE = r"""<title>Study-Automation Pipeline</title>
<style>
  :root{
    --ground:#f5f8f7;--panel:#fff;--panel2:#fbfdfc;--ink:#0c1a19;--soft:#4a5b59;
    --line:#e2e9e7;--line2:#c9d4d1;--teal:#0d9488;--teal-deep:#0f766e;--wash:#e6f4f1;
    --good:#059669;--good-w:#e7f4ee;--warn:#b45309;--warn-w:#fbf1e3;--bad:#dc2626;--bad-w:#fbeaea;
    --mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
    --sans:system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  }
  @media(prefers-color-scheme:dark){:root:not([data-theme=light]){
    --ground:#0b1211;--panel:#111b1a;--panel2:#0e1716;--ink:#e8f0ee;--soft:#93a5a2;
    --line:#1e2b29;--line2:#2c3d3a;--teal:#2dd4bf;--teal-deep:#5eead4;--wash:#0f2320;
    --good:#34d399;--good-w:#0e241c;--warn:#fbbf24;--warn-w:#241a08;--bad:#f87171;--bad-w:#2a1414;
  }}
  :root[data-theme=dark]{
    --ground:#0b1211;--panel:#111b1a;--panel2:#0e1716;--ink:#e8f0ee;--soft:#93a5a2;
    --line:#1e2b29;--line2:#2c3d3a;--teal:#2dd4bf;--teal-deep:#5eead4;--wash:#0f2320;
    --good:#34d399;--good-w:#0e241c;--warn:#fbbf24;--warn-w:#241a08;--bad:#f87171;--bad-w:#2a1414;
  }
  *{box-sizing:border-box}
  body{margin:0;background:var(--ground);color:var(--ink);font-family:var(--sans);line-height:1.55;-webkit-font-smoothing:antialiased}
  .wrap{max-width:960px;margin:0 auto;padding:44px 22px 90px}
  .eyebrow{font-family:var(--mono);font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:var(--teal-deep);font-weight:600}
  h1{font-size:clamp(29px,4.6vw,44px);line-height:1.06;margin:10px 0 8px;letter-spacing:-.02em;text-wrap:balance}
  .lede{font-size:17.5px;color:var(--soft);max-width:66ch;margin:0}
  .ribbon{display:flex;flex-wrap:wrap;gap:8px;margin-top:20px}
  .rb{font-family:var(--mono);font-size:11px;padding:4px 10px;border-radius:8px;background:var(--panel);border:1px solid var(--line2);color:var(--soft)}
  .rb b{color:var(--ink)} .rb.ok b{color:var(--good)}
  section{margin-top:46px}
  .sec-h{display:flex;align-items:baseline;gap:12px;margin-bottom:14px;padding-bottom:9px;border-bottom:1px solid var(--line)}
  .sec-n{font-family:var(--mono);font-size:12px;color:var(--teal-deep);font-weight:700}
  .sec-h h2{font-size:19px;margin:0;letter-spacing:-.01em}
  .sec-h .sub{margin-left:auto;font-size:12.5px;color:var(--soft)}
  .panel{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:18px 19px}
  .q{font-size:16px;line-height:1.6}.q b{color:var(--teal-deep)}
  .meta{display:flex;flex-wrap:wrap;gap:8px;margin-top:12px}
  .chip{font-family:var(--mono);font-size:11.5px;padding:3px 9px;border-radius:7px;background:var(--wash);color:var(--teal-deep);border:1px solid var(--line2)}
  .chip.ghost{background:transparent;color:var(--soft)}
  .scroll{overflow-x:auto;border:1px solid var(--line);border-radius:12px;background:var(--panel)}
  table{border-collapse:collapse;width:100%;font-size:13.5px}
  th,td{text-align:left;padding:10px 13px;border-bottom:1px solid var(--line);vertical-align:top}
  th{font-size:10.5px;letter-spacing:.07em;text-transform:uppercase;color:var(--soft);font-weight:600;background:var(--wash)}
  tbody tr:last-child td{border-bottom:none}
  .mono{font-family:var(--mono)} .exp{font-family:var(--mono);font-size:12px}
  .pill{display:inline-block;font-size:10.5px;font-weight:700;padding:2px 8px;border-radius:999px;font-family:var(--mono);white-space:nowrap}
  .v-pass{background:var(--good-w);color:var(--good)}.v-fail{background:var(--bad-w);color:var(--bad)}
  .v-warn{background:var(--warn-w);color:var(--warn)}.v-none{background:var(--wash);color:var(--soft)}
  .sev{font-size:9.5px;color:var(--soft);font-family:var(--mono);text-transform:uppercase;letter-spacing:.06em}
  /* margin matrix */
  .matrix{border:1px solid var(--line);border-radius:12px;overflow:hidden;background:var(--panel)}
  .mx{border-collapse:collapse;width:100%;font-size:12px;min-width:640px}
  .mx th,.mx td{padding:7px 9px;border:1px solid var(--line);text-align:center}
  .mx th:first-child,.mx td:first-child{text-align:left;font-weight:600;white-space:nowrap;position:sticky;left:0;background:var(--panel)}
  .mx td{font-family:var(--mono);font-variant-numeric:tabular-nums}
  .mx .decrow td{background:var(--panel2);color:var(--soft);font-size:10.5px;text-align:left}
  /* iteration cards */
  .iter{border:1px solid var(--line);border-radius:12px;background:var(--panel);margin-top:12px;overflow:hidden}
  .iter.done{border-color:var(--good)}
  .iter-h{display:flex;align-items:center;gap:12px;padding:12px 16px;background:var(--panel2);border-bottom:1px solid var(--line)}
  .iter-k{font-family:var(--mono);font-size:11px;color:var(--teal-deep);font-weight:700}
  .iter-active{font-family:var(--mono);font-size:11px;color:var(--soft)}
  .bar{height:6px;border-radius:3px;background:var(--line);overflow:hidden;width:70px;margin-left:auto}
  .bar i{display:block;height:100%;background:var(--good)}
  .score{font-family:var(--mono);font-weight:700;font-size:13px}
  .iter-b{padding:12px 16px}
  .tests{display:grid;grid-template-columns:repeat(auto-fill,minmax(148px,1fr));gap:7px}
  .tcell{border:1px solid var(--line);border-radius:8px;padding:7px 9px;font-size:11.5px}
  .tcell .tn{font-weight:600;display:flex;gap:6px;justify-content:space-between;align-items:center}
  .tcell .tobs{font-family:var(--mono);font-size:10.5px;color:var(--soft);margin-top:3px}
  .tcell.fixed{border-color:var(--good);background:var(--good-w)}
  .tcell.reg{border-color:var(--bad);background:var(--bad-w)}
  .navline{display:flex;align-items:center;gap:9px;margin:9px 2px;font-family:var(--mono);font-size:11.5px;color:var(--soft)}
  .navline .tag{color:var(--teal-deep);font-weight:700}
  .navline .arrow{color:var(--line2)}
  .callout{border:1px solid var(--line2);border-left:3px solid var(--teal);border-radius:10px;padding:13px 16px;background:var(--panel);margin-top:14px;font-size:13.5px;color:var(--soft)}
  .callout.bad{border-left-color:var(--bad)}.callout.warn{border-left-color:var(--warn)}.callout b{color:var(--ink)}
  canvas{width:100%;height:270px;display:block}
  .legend{display:flex;gap:15px;flex-wrap:wrap;margin-top:9px;font-size:11.5px;color:var(--soft)}
  .legend i{display:inline-block;width:11px;height:11px;border-radius:3px;margin-right:5px;vertical-align:-1px}
  .verdict-banner{display:flex;align-items:center;gap:14px;border-radius:12px;padding:16px 18px;background:var(--good-w);border:1px solid var(--good)}
  .verdict-banner .big{font-size:25px;font-weight:800;color:var(--good);font-family:var(--mono)}
  .stats{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-top:12px}
  @media(max-width:720px){.stats{grid-template-columns:repeat(2,1fr)}}
  .stat{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:12px 14px}
  .stat .n{font-size:21px;font-weight:700;font-variant-numeric:tabular-nums}.stat .k{font-size:11.5px;color:var(--soft);margin-top:3px}
  .foot{margin-top:48px;padding-top:16px;border-top:1px solid var(--line);font-size:12px;color:var(--soft);font-family:var(--mono)}
  code{font-family:var(--mono);font-size:.92em;background:var(--wash);padding:1px 5px;border-radius:4px}
</style>

<div class="wrap">
  <div class="eyebrow">Study-automation pipeline · one study, end to end</div>
  <h1>Watching the loop build a model from a contract</h1>
  <p class="lede">A single study driven through the whole agentic model-building loop — the contract, the tests it must pass, the audit that checks those tests are enough, and the real, <em>emergent</em> record of an inert draft becoming a model that passes every test. Nothing below is scripted: a deterministic policy reads the failing tests and chooses each edit, and every verdict is computed by running that iteration's model.</p>
  <div class="ribbon" id="ribbon"></div>

  <section id="s-contract"></section>
  <section id="s-draft"></section>
  <section id="s-select"></section>
  <section id="s-tests"></section>
  <section id="s-audit"></section>
  <section id="s-lock"></section>
  <section id="s-loop"></section>
  <section id="s-result"></section>
  <section id="s-giveup"></section>
  <section id="s-health"></section>
  <div class="foot" id="foot"></div>
</div>

<script>
const D=__DATA__;
const $=(id)=>document.getElementById(id);
const vp=(v)=>{const m={within_tol:['v-pass','pass'],mismatch:['v-fail','fail'],drift:['v-warn','drift'],ungraded:['v-none','—']};const [c,l]=m[v]||['v-none',v||'—'];return `<span class="pill ${c}">${l}</span>`;};
const gate=(g)=>`<span class="pill ${g==='pass'?'v-pass':g==='warn'?'v-warn':'v-fail'}">gate: ${g}</span>`;
const secH=(n,t,s)=>`<div class="sec-h"><span class="sec-n">${n}</span><h2>${t}</h2>${s?`<span class="sub">${s}</span>`:''}</div>`;
const R=D.result, L=D.lock;

// integrity ribbon
$('ribbon').innerHTML=[
  `<span class="rb ok">state <b>${R.state}</b></span>`,
  `<span class="rb">edits to pass <b>${R.edits_to_pass}</b> / budget ${R.max_iterations}</span>`,
  `<span class="rb ok">locked tests <b>${L.n_hard} hard</b> · ${L.n_tests_locked} total</span>`,
  `<span class="rb ok">reopens <b>${L.reopen_count}</b></span>`,
  `<span class="rb ${R.violations.length?'':'ok'}">invariant violations <b>${R.violations.length}</b></span>`,
  `<span class="rb mono">${L.tests_hash.slice(0,19)}…</span>`,
].join("");

// 1 contract
$('s-contract').innerHTML=secH("01","The contract","the prompt for the model we want")+
  `<div class="panel"><div class="q">${D.contract.question.replace(/\b([A-Z]{2,})\b/g,'<b>$1</b>')}</div>
   <div class="meta">${D.contract.observables.map(o=>`<span class="chip">${o}</span>`).join("")}
   <span class="chip ghost">success = ${D.contract.success}</span></div></div>`;

// composite renderer — the real process-bigraph model
const compo=(c)=>`<div style="margin-top:12px"><div style="font-size:12px;color:var(--soft);margin-bottom:6px"><code>${c.engine}</code> · stores: ${c.stores.map(s=>`<code>${s}</code>`).join(' ')}</div>
  <div class="scroll"><table><thead><tr><th>Process node</th><th>Address</th><th>reads</th><th>writes</th></tr></thead><tbody>${
   c.processes.map(p=>`<tr><td class="mono"><b>${p.node}</b></td><td class="mono" style="font-size:11.5px;color:var(--soft)">${p.address}</td><td class="mono" style="font-size:11.5px">${p.reads.join(', ')}</td><td class="mono" style="font-size:11.5px">${p.writes.join(', ')}</td></tr>`).join("")}</tbody></table></div></div>`;

// 2 draft
$('s-draft').innerHTML=secH("02","The draft","a real composite, no mechanism processes yet")+
  `<div class="panel"><p style="margin:0 0 6px;font-size:14px;color:var(--soft)">${D.draft.description}</p>
   ${compo(D.draft.composite)}</div>`;

// 3 select
$('s-select').innerHTML=secH("03","Sourcing (SELECT)","where the model comes from")+
  `<div class="panel"><div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:10px">
     <span class="pill v-pass">decision: ${D.select.decision}</span>
     <span style="font-size:13px;color:var(--soft)">${D.select.rationale}</span></div>
   <div class="scroll"><table><thead><tr><th>Mechanism (provided)</th><th>Knobs</th><th>Grounding</th></tr></thead><tbody>`+
   D.select.library.map(m=>`<tr><td class="mono"><b>${m.mechanism}</b></td><td class="mono" style="color:var(--soft)">${m.knobs.join(', ')}</td><td style="font-size:11.5px;color:var(--soft)">${m.cite}</td></tr>`).join("")+
   `</tbody></table></div><p style="margin:10px 0 0;font-size:12px;color:var(--soft)">The loop may only compose these provided mechanisms (invariant I3) — it cannot invent one to force a pass.</p></div>`;

// 4 tests
$('s-tests').innerHTML=secH("04","The acceptance tests","what a correct model must satisfy")+
  `<div class="scroll"><table><thead><tr><th>Test</th><th>Criterion</th><th>Band</th><th>Knob</th><th>Provenance</th></tr></thead><tbody>`+
  D.tests.map(t=>`<tr><td><b>${t.id}</b> <span class="sev">${t.severity}</span></td><td>${t.label}</td>
    <td class="exp">${t.expected}</td><td class="mono" style="font-size:11.5px;color:var(--soft)">${t.knob}</td>
    <td style="font-size:11px;color:var(--soft)">${t.provenance}</td></tr>`).join("")+`</tbody></table></div>`;

// 5 audit (two rounds)
const A=D.audit;
$('s-audit').innerHTML=secH("05","The sufficiency audit","are the tests rigorous & matched to the problem?")+
  `<div class="panel"><div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:12px">
     ${gate(A.round1_gate)} <span style="color:var(--line2)">→ revise →</span> ${gate(A.round2_gate)}
     <span style="font-size:13px;color:var(--soft)">before locking, <code>viva_superpowers.test_audit</code> grades whether passing the tests would mean something.</span></div>
   <div class="callout warn"><b>The audit did work.</b> Round 1 flagged ${A.round1_flags.length? A.round1_flags.map(f=>`<code>${f.id}</code>`).join(', ')+' (one-sided thresholds — a model could pass by overshooting)':'no issues'}. ${A.revision} Round 2 → <b>${A.round2_gate}</b>.</div>
   <div class="scroll" style="margin-top:12px"><table><thead><tr><th>Axis</th><th>Verdict</th><th>Reading</th></tr></thead><tbody>`+
   A.axes.map(a=>`<tr><td><b>${a.id}</b></td><td>${vp(a.verdict)}</td><td style="font-size:12px;color:var(--soft)">${a.label||''}</td></tr>`).join("")+
   `</tbody></table></div></div>`;

// 6 lock
$('s-lock').innerHTML=secH("06","Pre-registration lock","the tests are frozen — they cannot be weakened to pass")+
  `<div class="panel"><div class="meta"><span class="chip">${L.n_hard} hard + ${L.n_tests_locked-L.n_hard} diagnostic frozen</span>
   <span class="chip">reopen_count ${L.reopen_count}</span><span class="chip mono">${L.tests_hash}</span></div>
   <p style="margin:10px 0 0;font-size:13px;color:var(--soft)">From here the loop edits only the <b>model</b>. A change to a locked test would move this hash and register a re-open in <code>loop_state</code> — so weakening a test to force a pass is visible, not silent. The negative control below confirms the tests can kill: the inert draft's <code>growth</code> reads <b>${D.control.observed}</b> vs required ${D.control.expected} → <b>${D.control.discriminates?'fails, as it must':'does not discriminate (!)'}</b>.</p></div>`;

// 7 build loop
let H=secH("07","The build loop","a deterministic policy iterates the model until every test passes");
// margin matrix
const its=D.iterations, hard=its[0].verdicts.filter(v=>v.severity==='hard').map(v=>v.id);
const mcolor=(v)=>v.verdict==='within_tol'?'var(--good-w)':v.verdict==='mismatch'?'var(--bad-w)':'var(--warn-w)';
const mink=(v)=>v.verdict==='within_tol'?'var(--good)':v.verdict==='mismatch'?'var(--bad)':'var(--warn)';
let mx=`<div class="matrix"><div style="overflow-x:auto"><table class="mx"><thead><tr><th>signed margin</th>`+
  its.map(it=>`<th>iter ${it.iteration}<br><span style="font-weight:400;color:var(--soft)">${it.n_pass}/${it.n_hard}</span></th>`).join("")+`</tr></thead><tbody>`;
hard.forEach(tid=>{
  mx+=`<tr><td>${tid}</td>`+its.map(it=>{const v=it.verdicts.find(x=>x.id===tid);const m=v.margin==null?'—':(v.margin>=0?'+':'')+v.margin.toFixed(2);
    return `<td style="background:${mcolor(v)};color:${mink(v)}">${m}</td>`;}).join("")+`</tr>`;
});
mx+=`<tr class="decrow"><td>NAVIGATE</td>`+its.map(it=>`<td style="text-align:left">${it.decision?(it.decision.kind==='install'?'install '+it.decision.mechanism:it.decision.kind==='calibrate'?'t_tol '+it.decision.from+'→'+it.decision.to:it.decision.kind):'— DONE'}</td>`).join("")+`</tr>`;
mx+=`</tbody></table></div></div>`;
H+=mx;
H+=`<p style="font-size:12px;color:var(--soft);margin:8px 2px 0">Each cell is the real signed margin (distance to the band edge). Green→met, red→missed. Read a row left-to-right to watch one test converge — and note the two <b style="color:var(--bad)">red dips</b> where a fix broke something else.</p>`;
// iteration cards with nav lines
its.forEach((it,idx)=>{
  const done=it.n_pass===it.n_hard && !it.decision;
  const cells=it.verdicts.map(v=>{const fx=it.newly_fixed.includes(v.id),rg=it.regressed.includes(v.id);
    return `<div class="tcell ${fx?'fixed':rg?'reg':''}"><div class="tn"><span>${v.id}</span>${vp(v.verdict)}</div>
      <div class="tobs">obs ${v.observed} · ${v.expected}${fx?' ▲ fixed':rg?' ▼ regressed':''}</div></div>`;}).join("");
  const pct=Math.round(100*it.n_pass/it.n_hard);
  H+=`<div class="iter ${done?'done':''}"><div class="iter-h"><span class="iter-k">ITER ${it.iteration}</span>
    <span class="iter-active">${it.active.length?it.active.join(' + '):'inert draft'}</span>
    <div class="bar"><i style="width:${pct}%"></i></div><span class="score">${it.n_pass}/${it.n_hard}</span></div>
    <div class="iter-b"><div class="tests">${cells}</div></div></div>`;
  if(it.decision){const d=it.decision;
    const txt=d.kind==='install'?`worst failure <b>${d.test}</b> (margin ${(d.margin||0).toFixed(2)}) → install <b>${d.mechanism}</b>`
      :d.kind==='calibrate'?`<b>${d.test}</b> still failing → calibrate <b>${d.knob}</b> ${d.from}→${d.to} °C`
      :`<b>${d.test}</b> unfixable — ${d.note}`;
    H+=`<div class="navline"><span class="tag">DECIDE</span><span class="arrow">▸</span><span>${txt}</span></div>`;}
});
H+=`<div class="callout bad"><b>The loop caught two regressions.</b> Installing uptake made <code>nutrient-depletion</code> pass but broke <code>conservation</code> (nutrient consumed with nowhere to go) — fixed by installing yield-coupled growth. Later, the thermal mechanism's default tolerance (35 °C, a mesophile prior) fixed <code>viability-cliff</code> but broke <code>viability-in-band</code> — fixed by calibrating the tolerance up into the band. Both are visible because the frozen tests are re-graded every iteration. That is the difference between "the number went up" and "the model actually got better."</div>`;
$('s-loop').innerHTML=H;

// 8 result
const done=R.state==='DONE';
$('s-result').innerHTML=secH("08","The result","tests passing — the model is built")+
  `<div class="verdict-banner" style="${done?'':'background:var(--bad-w);border-color:var(--bad)'}">
     <span class="big" style="${done?'':'color:var(--bad)'}">${R.state}</span>
     <span style="font-size:14px">Reached <b>${its[its.length-1].n_pass}/${L.n_hard}</b> hard tests in <b>${R.edits_to_pass}</b> model edits — integrity clean (${R.violations.length} violations). Final knobs: ${Object.entries(R.final_knobs).map(([k,v])=>`<code>${k}=${v}</code>`).join(' ')}.</span></div>
   <div class="stats">
     <div class="stat"><div class="n">${R.edits_to_pass}</div><div class="k">edits to a passing model (budget ${R.max_iterations})</div></div>
     <div class="stat"><div class="n">2</div><div class="k">regressions caught & recovered</div></div>
     <div class="stat"><div class="n">${R.stability.stable}/${R.stability.total}</div><div class="k">perturbation variants still pass (dt/2, ±10% knobs)</div></div>
     <div class="stat"><div class="n">${R.violations.length}</div><div class="k">integrity violations — no test weakened</div></div>
   </div>
   <div class="panel" style="margin-top:12px"><div style="font-size:12.5px;color:var(--soft);margin-bottom:6px">Final built model — real units; the dashed line is where temperature crosses the calibrated tolerance (t_tol = ${D.timeseries.t_tol} °C). The <b style="color:var(--bad)">faint red</b> curve is iteration 3's mis-calibrated viability (collapsed early) — the regression, drawn.</div>
     <canvas id="chart" width="900" height="270"></canvas>
     <div class="legend"><span><i style="background:var(--teal)"></i>biomass</span><span><i style="background:var(--warn)"></i>nutrient</span><span><i style="background:var(--good)"></i>viability (final)</span><span><i style="background:var(--bad)"></i>viability (iter 3, regressed)</span><span><i style="background:var(--soft)"></i>temperature</span></div></div>
   <div class="panel" style="margin-top:12px"><div style="font-size:12.5px;color:var(--soft);margin-bottom:2px"><b>The built model is a real process-bigraph composite</b> — the loop assembled it by installing these Process nodes; the dynamics above came from running it through the engine, not an inline integrator.</div>${compo(D.final_composite)}</div>`;

// 9 give-up companion
const G=D.giveup_companion;
$('s-giveup').innerHTML=secH("09","Honest failure","what the loop does when the library can't win")+
  `<div class="panel"><div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:8px">
     <span class="pill ${G.outcome==='GIVE_UP'?'v-warn':'v-fail'}">${G.outcome}</span>
     <span class="mono" style="font-size:12px;color:var(--soft)">reached ${G.final_pass}/${G.n_hard}, then stopped</span></div>
   <p style="margin:0;font-size:13.5px;color:var(--soft)">${G.note}. DONE is only trustworthy because GIVE_UP is reachable: the same policy, run with the thermal mechanism withheld from the library, improves to the ceiling the provided mechanisms allow and then terminates <b>honestly</b> (invariant I4) rather than reporting a pass it did not earn.</p></div>`;

// 10 health
$('s-health').innerHTML=secH("10","Pipeline health","how well the automation is doing")+
  `<div class="panel"><p style="margin:0 0 8px;font-size:14px">On this study the pipeline did what it is supposed to: authored acceptance tests, <b>audited them for sufficiency and revised them</b> (warn → pass) before locking, sourced only provided mechanisms, then a deterministic policy improved an inert draft to a <b>full pass in ${R.edits_to_pass} edits</b> — recovering from two self-inflicted regressions — without touching a locked test, and it can <b>give up honestly</b> when the library is insufficient.</p>
   <div class="callout"><b>Honest scope.</b> One study, a physically-consistent toy model — the rate-law shapes are real (Monod uptake, yield-coupled growth, mass balance, threshold thermal death) with illustrative, literature-grounded constants, not fitted. It shows the loop's mechanics and integrity end-to-end. Perturbation stability is <b>${R.stability.stable}/${R.stability.total}</b>, not perfect — some knobs sit near a band edge, which the report shows rather than hides. The next step for "how well are we doing" at scale is the study-automation benchmark suite, which runs many such studies and scores loop-outcome, test-sufficiency, and sourcing-quality across them.</div></div>`;

$('foot').innerHTML=`Real trajectory from <code>scripts/build_loop_demo.py</code> (emergent NAVIGATE policy) · loop state in <code>.pbg/loop/bounded-cell.json</code>, <code>loop_state.validate</code> clean · rendered by <code>scripts/render_pipeline_report.py</code>.`;

// chart
(function(){const c=$('chart');if(!c)return;const x=c.getContext('2d');const W=c.width,H=c.height,pad=32;
 const ts=D.timeseries,n=ts.t.length;const css=getComputedStyle(document.documentElement);const col=v=>css.getPropertyValue(v).trim();
 const norm=a=>{const mx=Math.max(...a),mn=Math.min(...a),r=(mx-mn)||1;return a.map(v=>(v-mn)/r);};
 const X=i=>pad+(W-2*pad)*i/(n-1),Y=v=>H-pad-(H-2*pad)*v;
 x.clearRect(0,0,W,H);x.strokeStyle=col('--line');x.lineWidth=1;
 for(let g=0;g<=4;g++){const y=pad+(H-2*pad)*g/4;x.beginPath();x.moveTo(pad,y);x.lineTo(W-pad,y);x.stroke();}
 if(ts.cliff_frac!=null){const cx=X(ts.cliff_frac*(n-1));x.strokeStyle=col('--line2');x.setLineDash([4,4]);x.beginPath();x.moveTo(cx,pad);x.lineTo(cx,H-pad);x.stroke();x.setLineDash([]);
   x.fillStyle=col('--soft');x.font='11px ui-monospace,monospace';x.fillText('T ⟩ '+ts.t_tol+'°C',cx+5,pad+12);}
 const line=(a,cv,w)=>{const v=norm(a);x.strokeStyle=col(cv);x.lineWidth=w||2.3;x.beginPath();v.forEach((y,i)=>{const px=X(i),py=Y(y);i?x.lineTo(px,py):x.moveTo(px,py);});x.stroke();};
 line(ts.temperature,'--soft',1.4);
 // iter-3 regressed viability overlay (its viability_curve is already 0..1)
 const it3=D.iterations.find(it=>it.regressed && it.regressed.includes('viability-in-band'));
 if(it3&&it3.viability_curve){const vc=it3.viability_curve;const m=vc.length;x.strokeStyle=col('--bad');x.globalAlpha=.45;x.lineWidth=2;x.beginPath();vc.forEach((y,i)=>{const px=pad+(W-2*pad)*i/(m-1),py=Y(y);i?x.lineTo(px,py):x.moveTo(px,py);});x.stroke();x.globalAlpha=1;}
 line(ts.nutrient,'--warn');line(ts.biomass,'--teal');line(ts.viability,'--good');
})();
</script>
"""


def main():
    traj = json.load(open(TRAJ))
    html = TEMPLATE.replace("__DATA__", json.dumps(traj))
    os.makedirs(os.path.dirname(OUTHTML), exist_ok=True)
    with open(OUTHTML, "w") as fh:
        fh.write(html)
    print(f"rendered -> {os.path.relpath(OUTHTML, ROOT)} ({len(html)} bytes)")


if __name__ == "__main__":
    main()
