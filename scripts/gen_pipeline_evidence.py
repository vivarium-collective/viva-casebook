"""Generate docs/pipeline-evidence.html: a self-contained summary of the improved
agentic pipeline's LIVE agent runs (Fable review response), in the redesigned-report
visual style. Reads the committed live-run records from the workspace."""
import html, json, os
HERE = os.path.dirname(os.path.abspath(__file__))
D_DIR = os.path.join(HERE, os.pardir, "workspace", "investigations", "model-building")
DOCS = os.path.join(HERE, os.pardir, "docs")
def _L(f):
    p = os.path.join(D_DIR, f)
    return json.load(open(p)) if os.path.exists(p) else None
D = {"menu": {t: _L(f"{t}_agent_live.json") for t in ("diauxie","diagnosis","bistable") if _L(f"{t}_agent_live.json")},
     "repair": _L("repair_suite_live.json"), "author": _L("author_agent_live.json"),
     "author_tests": _L("author_tests_live.json")}
esc = lambda s: html.escape(str(s)) if s is not None else ""

CSS = """
:root{--paper:#FAF9F6;--surface:#FFFFFF;--sunken:#F4F2ED;--ink:#1F1D1B;--ink-2:#57534E;--ink-3:#8A857D;
--line:#E7E4DE;--line-2:#D8D4CC;--accent:#0F766B;--accent-soft:#0F766B18;--pass:#1A7F5A;--pass-soft:#1A7F5A18;
--warn:#A16207;--warn-soft:#A1620714;--chip:#F1EFEA;
--serif:"Iowan Old Style","Palatino Nova",Palatino,Georgia,serif;--sans:-apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif;--mono:ui-monospace,"SF Mono",Menlo,monospace;}
@media(prefers-color-scheme:dark){:root:not([data-theme=light]){--paper:#161513;--surface:#1E1C19;--sunken:#232019;--ink:#EDEAE3;--ink-2:#A8A29B;--ink-3:#78736B;--line:#37332D;--line-2:#453F37;--accent:#3FB9A5;--accent-soft:#3FB9A526;--pass:#43C08D;--pass-soft:#43C08D1f;--warn:#D9A036;--warn-soft:#D9A0361c;--chip:#2A2723;}}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font-family:var(--sans);font-size:16px;line-height:1.6;-webkit-font-smoothing:antialiased}
.wrap{max-width:920px;margin:0 auto;padding:0 24px}
.mast{padding:52px 0 8px}.mast .eyebrow{color:var(--ink-3);font-size:12.5px;letter-spacing:.06em;text-transform:uppercase;font-family:var(--mono)}
.mast h1{font-family:var(--serif);font-weight:600;font-size:40px;line-height:1.1;margin:12px 0 0;letter-spacing:-.01em;max-width:22ch;text-wrap:balance}
.mast .lede{color:var(--ink-2);font-size:17px;margin:16px 0 0;max-width:74ch}
.sec-h{display:flex;align-items:baseline;gap:12px;margin:48px 0 6px}.sec-h h2{font-family:var(--serif);font-size:24px;font-weight:600;margin:0}.sec-h .rule{flex:1;height:1px;background:var(--line)}
.sub{color:var(--ink-2);font-size:14.5px;max-width:76ch;margin:2px 0 16px}
.card{background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:22px 24px;margin:14px 0;box-shadow:0 1px 2px rgba(30,25,20,.04)}
.card.pass{border-left:3px solid var(--pass)}
.card h3{font-family:var(--serif);font-size:19px;font-weight:600;margin:0 0 2px}
.chip{display:inline-flex;align-items:center;gap:5px;font-size:12px;font-weight:600;padding:3px 10px;border-radius:999px;background:var(--chip);color:var(--ink-2)}
.chip.pass{color:var(--pass);background:var(--pass-soft)}.chip.mono{font-family:var(--mono);font-size:11.5px}
.chiprow{display:flex;gap:7px;flex-wrap:wrap;align-items:center;margin:6px 0}
.reason{color:var(--ink-2);font-size:13.5px;line-height:1.55;margin:8px 0 0;border-left:2px solid var(--line-2);padding-left:12px;font-style:italic}
.step{display:flex;gap:10px;align-items:baseline;padding:3px 0;font-size:13.5px}.step .mono{font-family:var(--mono);color:var(--ink-3);min-width:26px}
.callout{border:1px solid var(--line-2);border-left:3px solid var(--warn);background:var(--warn-soft);border-radius:10px;padding:14px 16px;margin:16px 0;font-size:13.5px;color:var(--ink-2)}
.callout b{color:var(--ink)}
code{font-family:var(--mono);font-size:.88em;background:var(--sunken);padding:1px 5px;border-radius:5px}
.kpi{display:flex;gap:22px;flex-wrap:wrap;margin:18px 0;border:1px solid var(--line);border-radius:12px;background:var(--surface);padding:16px 20px}
.kpi .n{font-family:var(--serif);font-size:24px;font-weight:600}.kpi .l{color:var(--ink-2);font-size:12.5px}
footer{border-top:1px solid var(--line);margin-top:52px;padding:22px 0 60px;color:var(--ink-3);font-size:12.5px;font-family:var(--mono)}
"""

MENU_BLURB = {"diauxie": "Diauxic growth (glucose→lactose)", "diagnosis": "Ambiguous diagnosis (why is biomass low?)",
              "bistable": "Bistable genetic switch"}


def menu_section():
    cards = []
    for t, d in D["menu"].items():
        run = d["runs"][0]
        steps = "".join(
            f'<div class="step"><span class="mono">i{i}</span><span><b>{esc(", ".join(s["active"]) or "empty draft")}</b>'
            f' — {esc(s.get("reasoning",""))}</span></div>' for i, s in enumerate(run["steps"]))
        cards.append(
            f'<div class="card pass"><h3>{esc(MENU_BLURB.get(t,t))}</h3>'
            f'<div class="chiprow"><span class="chip pass">✓ {esc(run["state"])} · {run.get("edits","?")} edits</span>'
            f'<span class="chip mono">{esc(d.get("model",""))}</span>'
            f'<span class="chip mono">n={esc(d.get("summary",{}).get("n_runs",1))}</span></div>{steps}</div>')
    return (
        '<div class="sec-h"><h2>Live agents on the menu tasks</h2><span class="rule"></span></div>'
        '<p class="sub">Real Claude sub-agents drive the environment turn by turn, reasoning from graded '
        'verdicts and a functional mechanism card (no test→mechanism answer key). These replace the old '
        'hand-typed transcripts.</p>' + "".join(cards) +
        '<div class="callout">⚖️ <b>Honest reframe.</b> A brute-force enumerating baseline also solves these '
        'three in 3 edits each (the winning mechanism is one of ≤3 in the library). So these show the agent '
        'reasons <b>efficiently</b> — 1–2 minimal installs, no wasted edits — not that an agent is '
        '<b>required</b>. Necessity is shown by the tasks below, where the fix is not a library item.</div>')


def repair_section():
    r = D["repair"]
    if not r:
        return ""
    cards = []
    for run in r["runs"]:
        loc = run["localize"]
        fit = run["fit"]
        moved = ", ".join(f"{p}:{v}" for p, v in loc["moved_from_broken"].items())
        cards.append(
            f'<div class="card pass"><h3>Break <code>{esc(run["break_id"])}</code> '
            f'<span style="font-weight:400;color:var(--ink-3)">(opaque — the id does not name the parameter)</span></h3>'
            f'<div class="chiprow">'
            f'<span class="chip pass">✓ PE repaired · resim RMSD {esc(fit["resim_rmsd"])}</span>'
            f'<span class="chip mono">fit → {esc(fit["fitted"])}</span>'
            f'<span class="chip mono">{esc(fit.get("method",""))}</span></div>'
            f'<div class="reason"><b>Recall-free diagnosis (localize baseline):</b> PE fit all candidate '
            f'parameters {esc(D["repair"].get("candidate_parameters"))} jointly against the reference trace; '
            f'only <code>{esc(loc["diagnosed_parameter"])}</code> had to move (moved: {esc(moved)}) → '
            f'diagnosed the break by optimization, no canonical value consulted. '
            f'The break was <code>{esc(run["param"])}</code> ({esc(run["blurb"])}) '
            f'{esc(run["broken_value"])} → {esc(run["true_value"])}; diagnosis '
            f'{"correct" if loc["correct"] else "INCORRECT"}.</div></div>')
    return (
        '<div class="sec-h"><h2>Data-grounded biology — break &amp; repair by parameter estimation</h2><span class="rule"></span></div>'
        '<p class="sub">A kinetic model run in the real COPASI backend; one parameter is broken and must be '
        'repaired against the intact reference time-course. The repair oracle is <b>optimization, not '
        'recall</b> — COPASI Parameter Estimation fits the reference trace and recovers the true value, and a '
        'recall-free <b>localization</b> baseline fits all candidates and identifies the broken one by which '
        'must move. Break ids are opaque and the reference + broken traces are shown, so the diagnosis cannot '
        'come from a memorized number.</p>' + "".join(cards) +
        '<div class="callout">🔬 <b>Why this is stronger than the old version.</b> The earlier suite graded a '
        '<i>recalled</i> fix (the celebrity repressilator, diagnosed from "double the canonical value"). Here '
        'the oracle is a COPASI optimizer fitting the trace — celebrity-ness of the model no longer helps, '
        'because recall plays no role. Broadening to a corpus of non-celebrity models is the next step '
        '(each needs its own PE window tuning).</div>')


def author_section():
    a = D["author"]
    if not a:
        return ""
    run = a["runs"][0]
    return (
        '<div class="sec-h"><h2>Open action space — the agent authors a Process</h2><span class="rule"></span></div>'
        '<p class="sub">No mechanism menu: the agent must <b>write</b> new process-bigraph code, executed '
        'sandboxed in a subprocess with a timeout. Enumeration provably cannot solve this.</p>'
        f'<div class="card pass"><h3>Author a Process to drive X → target</h3>'
        f'<div class="chiprow"><span class="chip pass">✓ {esc(run["state"])} · {run.get("attempts","?")} attempt</span>'
        f'<span class="chip mono">cite: {esc(run.get("citation",""))}</span></div>'
        f'<div class="reason">{esc(run.get("reasoning",""))}</div>'
        f'<div class="step" style="margin-top:8px"><span class="mono">Δ</span><code>update → dX = k·(target − X)·interval</code></div></div>')


def author_tests_section():
    at = D["author_tests"]
    if not at:
        return ""
    fc = at["full_cycle"]
    catch = at["audit_catches_insufficiency_demo"]
    enforced = at.get("lock_enforced_demo", {})
    return (
        '<div class="sec-h"><h2>The AUTHOR phase — author + audit + lock its own tests</h2><span class="rule"></span></div>'
        '<p class="sub">The loop\'s real novelty: from an open question, acceptance tests are written, a '
        '<b>hardened audit</b> RUNS degenerate null models to check the tests reject them (executable, not a '
        'label), the tests are <b>locked with a pre-registration hash that build() re-verifies</b>, then a '
        'model is built that passes them. <i>This panel is a deterministic demonstration of the '
        'audit→lock→build machinery — no LLM in the loop; every verdict is real output of '
        '<code>author_tests_task.py</code>.</i></p>'
        f'<div class="card pass"><h3>Full cycle: question → author → hardened audit → lock → build</h3>'
        f'<div class="chiprow"><span class="chip pass">✓ built · {esc(fc.get("n_pass"))}/{esc(fc.get("n_hard"))} tests pass</span>'
        f'<span class="chip">audit: sufficient</span><span class="chip mono">lock sha256 {esc((fc.get("tests_hash") or "")[:10])}…</span>'
        f'<span class="chip">min/max bounded</span></div>'
        f'<div class="reason">{esc(fc.get("reasoning",""))}</div></div>'
        f'<div class="callout">🔎 <b>The audit rejects a plausible-looking suite.</b> A <code>final</code>-only '
        f'band (final≥4.5, final≤5.5) looks reasonable — but the hardened audit RUNS transient nulls and flags '
        f'that <b>{esc(", ".join(catch["degenerate_models_that_slip_through"]))}</b> slip through: a model that '
        f'spikes to 10⁶ mid-run and settles to ~5 passes a final-only test while violating "stays bounded". So '
        f'the suite cannot lock until it also bounds <code>max</code> and <code>min</code>. '
        + ('<b>And the lock is enforced:</b> editing the locked tests after pre-registration makes '
           '<code>build()</code> refuse to grade (hash mismatch). ' if enforced.get("build_refused") else '')
        + 'Not a classification label, not a promise.</div>')


def page():
    return (
        f"<title>Agentic Loop — Live Evidence</title><style>{CSS}</style>"
        '<div class="wrap"><div class="mast">'
        '<div class="eyebrow">viva-casebook · after the review</div>'
        '<h1>The agentic model-building loop, after the review</h1>'
        '<p class="lede">The pipeline after Fable\'s review: honest evaluation (a fair enumerating baseline), '
        'an open action space, data-grounded biology, and an audited, pre-registered test-authoring phase. '
        'Provenance is stated per panel — the menu tasks are <b>live</b> Claude sub-agent runs (single '
        'trajectory, n=1); the AUTHOR-phase panel is a <b>deterministic demonstration</b> of the '
        'audit/lock/build machinery. Every verdict shown is real engine output.</p>'
        '<div class="kpi">'
        '<div><div class="n">3</div><div class="l">live menu-task runs (n=1 each)</div></div>'
        '<div><div class="n">COPASI</div><div class="l">parameter-estimation repair oracle</div></div>'
        '<div><div class="n">1</div><div class="l">Process authored from scratch</div></div>'
        '<div><div class="n">sha256</div><div class="l">enforced pre-registration lock</div></div></div>'
        '</div>'
        + menu_section() + repair_section() + author_section() + author_tests_section()
        + '<footer>Rendered from committed live-run records in workspace/investigations/model-building/*.json · '
          'viva-casebook</footer></div>')


os.makedirs(DOCS, exist_ok=True) or open(os.path.join(DOCS, "pipeline-evidence.html"), "w").write(page())
print("wrote pipeline-evidence.html", os.path.getsize(os.path.join(DOCS, "pipeline-evidence.html")), "bytes")
