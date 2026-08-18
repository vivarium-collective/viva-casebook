# Agentic pipeline — improvement plan (from Fable's review)

Status of the review's recommendations:

- **Done & pushed:** integrity bugs (spurious I1 violation, `library_card` answer-key
  leak, hardcoded scorecard) and the **fair enumerating baseline** (#1a) — run for
  real; brute-force solves diauxie/diagnosis/bistable in 3 edits each, and the
  roadmap now says so.
- **This plan** covers the three larger changes + the AUTHOR-phase demo:
  **#1b live logged agent runs · #2 open action space · #3 data-grounded tests ·
  #4 the AUTHOR phase.**

The one-line thesis of the fix: today the casebook proves *efficient reasoning on a
shared substrate*; to prove *an agent is required to build science-relevant models*
we need real agents (not transcripts), a real action space (not menus), and real
ground truth (not author-set bands).

---

## Sequencing (why this order)

```
#1b live harness  ──►  #2 open action space  ──►  #4 AUTHOR phase
      │                                           ▲
      └──────────►  #3 data-grounded tests  ──────┘
```

**#1b first.** It's the foundation and the highest-integrity single change: once a
real agent runs live through a checked-in harness, every later claim is made by an
agent, not by a hand-written `DECISIONS` array. It also has the least new substrate
risk (the environments already exist). #2 and #3 are only *meaningful* once a real
agent is exploring them. #4 (agent authors + audits its own tests) needs #1b (a live
agent) + #2 (a test-authoring action) + ideally #3 (a real question), so it lands last.

The existing env was rebuilt enough to run the menu tasks (a `.venv` with the local
ecosystem); **finishing it** (resolve the viva-munk↔spatio-flux type-version skew,
restore `pbg-cpm` for the multicell/CPM tasks) is a shared prerequisite tracked under
#1b Stage 0.

---

## #1b — Live, logged agent runs

**Goal.** Replace the six hardcoded `capture_*.py` `DECISIONS` arrays with a
checked-in harness that drives a *real* LLM through the environment and records the
verbatim transcript, model id, and outcome — including failures.

**Design.**
- `scripts/run_agent.py`: a harness that hands the model (a) the contract, (b) a
  `library_card` tool (post-leak-fix: mechanism *descriptions* + citations, never the
  test→mechanism map), and (c) a `step(active, knobs)` tool returning the graded
  per-test verdicts/margins. The model reasons turn-by-turn until DONE or a turn
  budget; the harness logs every message.
- Output: `*_agent_trajectory.json` gains `live: true`, `model`, `temperature`,
  `run_index`, and a `transcript` block; the replayed-`DECISIONS` path is retired.
- **n ≥ 5 runs per task**, all recorded. Report pass-rate, edit-count distribution,
  and failure modes — not a single curated win.

**Decision needed — how the harness talks to the model:**
- **(A) Anthropic Messages API + tool-use** (recommended): portable, reproducible,
  runs in CI-ish fashion; needs `ANTHROPIC_API_KEY` in the run env. The env becomes
  two tools the model calls.
- **(B) Claude Code Agent tool**: no API key, but only reproducible inside Claude
  Code and harder to check in as a standalone artifact.
Recommendation: **(A)**, with the transcript checked in so the *result* is auditable
even without re-running.

---

## #2 — Open the action space

**Goal.** Let the agent take actions the task author didn't enumerate, so "the policy
has no move" becomes a statement about the *problem*, not the menu.

**Design (three new action types, additive to the current install/knob):**
1. **Catalog install** — install *any* registered module/process from the shared core
   (`viva_casebook.core` already folds viva-munk / spatio-flux / viva-cpm; the
   `module_sourcing` audit already grades selection), not a curated ≤3.
2. **Author-a-Process** — the agent submits a small Python `Process`
   (`config_schema`, `inputs`/`outputs`, `update`); the harness validates it's a
   well-formed Process, registers it into the core, and wires it into the composite.
   **I3 reframed** from "provided-mechanisms-only" (menu membership) to
   "cited-mechanisms-only" (the authored Process must carry a mechanism citation) —
   this keeps the anti-fabrication guarantee while removing the straitjacket.
3. **Multi-knob calibrate / probe** — a `calibrate(params, target)` fit over several
   parameters at once (today's "calibration" is one blind knob step), and an
   agent-requested probe run (e.g. a small sweep) to gather observables before deciding.

**Decision needed — sandboxing of authored code:** run the authored `update()` in a
restricted namespace in-process (fast, lower isolation) vs a subprocess with a
resource/timeout guard (safer, slower). Recommendation: **subprocess + timeout** for
anything the agent authors, since the whole point is untrusted-ish generated code.

---

## #3 — Ground tests in data external to the author

**Goal.** Every hard test should trace to a dataset or reference simulation the
model-builder didn't write — so "DONE" means scientifically right, not "reproduces the
toy's intended behavior."

**Three candidate tasks, cheapest first:**
- **A. Data-grounded diauxie.** Fit the diauxie composite to a real growth-curve
  dataset; grade on *held-out* conditions. Same mechanism, real science.
  *Decision:* dataset source — digitize Monod 1949, or use a modern public
  diauxie/growth-curve dataset (licensing + digitization effort differ).
- **B. BioModels break-and-repair (the scalable one).** Take curated BioModels SBML
  entries (the ecosystem already has a BioModels multi-sim corpus), break one
  mechanism/parameter, give the agent the divergent timeseries vs the reference, and
  score diagnosis + repair. Ground truth objective, answer not in the prompt, scales
  to hundreds of tasks. *Decision:* reuse the existing BioModels corpus vs a fresh
  curated 20-model subset.
- **C. v2ecoli subsystem divergence.** "Acetate overflow diverges from a reference
  under condition X — find the responsible process and fix it," graded with the
  existing `report_card_verdict/v2` margins. Highest scientific value, biggest lift.

Recommendation: **B first** (scalable, objective, reuses existing substrate), then A
as the illustrative single case, C as the flagship.

---

## #4 — Demonstrate the AUTHOR phase

**Goal.** The loop's real novelty — agent turns an open question into *sufficient,
audited, pre-registered* tests — is demonstrated nowhere today (all seven test suites
are hand-written).

**Design.** One full `question → AUTHOR(agent writes tests) → AUDIT(catches a real
insufficiency) → LOCK → BUILD` cycle on a #3 data-grounded question, where the audit
genuinely rejects a first-draft test (too wide / gameable / uncovered mechanism) and
the agent revises before locking. Also **harden the audit** where it's leaned on
(Fable #5): the null-model check should *run* the knockout and confirm the test fails,
not accept an LLM promise; `has_discriminating_control` should require a real negative
control, not a `classification` label.

---

## Cross-cutting: reposition the casebook (Fable #6)

Until #1b–#3 land, frame the casebook as **protocol walkthroughs on a shared
substrate** (efficiency + reasoning-quality), not "evidence agents beat policies."
The framework's honest parts — pre-registration hashes, reopen trails, impossible
controls, `gamed_pass_rate`, perturbation stability — become the headline. (The
roadmap's fair-baseline caveat already starts this.)

---

## What I need from you to start building

1. **#1b harness:** approve **(A) Anthropic API** (needs a key in the run env) vs
   **(B) Agent-tool**.
2. **#3 first task:** approve **B (BioModels break-and-repair)** first, and whether to
   reuse the existing BioModels corpus.
3. **#2 sandboxing:** approve **subprocess+timeout** for authored Processes.
4. **Order confirmation:** #1b → (#2 ∥ #3) → #4, or a different priority.
