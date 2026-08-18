# viva-casebook

**How well is our model-building doing?** — a casebook of **capability-testing
investigations** for the vivarium model-building framework: studies whose object of
evaluation is the framework's *own* ability to build models well, kept separate from
any single paper or model.

> 🔁 **Flagship report — [the study-automation pipeline, end to end](https://vivarium-collective.github.io/viva-casebook/)**: one study driven through the whole model-building loop — contract → draft → tests → sufficiency audit → the *real, emergent* iteration trajectory from an inert draft to a model passing every test ([`docs/pipeline-report.html`](docs/pipeline-report.html)).
> 🤖 Head-to-head — [**LLM agent vs deterministic policy**](docs/agent-vs-policy.html): the same study built two ways, an actual LLM reasoning over the margins beside a hand-coded rule, on the same real composite.
> 🔗 And task #6 — [**Multiscale: the agent must author a translator**](docs/multiscale-agent-vs-policy.html): two models at different scales stay decoupled; the policy has no 'author a translator' move and gives up, while the LLM authors the translator and reasons the unit conversion that conserves mass.
> 🔬 And task #5 — [**Multicellular: the agent must choose a simulator**](docs/multicell-agent-vs-policy.html): the policy has no 'select simulator' move and gives up; the LLM picks CPM, composes a subcellular fate model, and produces a spatial differentiation gradient.
> 🧫 And where it matters — [**Diauxie: a task the policy can't solve**](docs/diauxie-agent-vs-policy.html): the policy consumes both substrates but gets the *regulation* wrong and gives up at 3/4; the LLM reasons that the fix is catabolite repression and reaches 4/4.
> 📊 Also: the [model-sourcing scorecard](docs/status.html).

The framework itself lives in
[viva-superpowers](https://github.com/vivarium-collective/viva-superpowers)
(`loop_state`, `module_sourcing`, `test_audit`, `benchmark_score`, and the
`/viva-model-build` · `/viva-audit-tests` · `/viva-benchmark` skills). This repo holds
the **investigations that exercise it** on real modules and render the evidence.

## Scorecard — `model-sourcing`

|  |  |
|---|---|
| ✅ **6 / 6** | sourcing decisions graded **correctly** by the audit |
| ✅ **4 / 4** | runnable tasks executed **live** on one shared core |
| 🧩 **3** | real modules reused — viva-munk · spatio-flux · viva-cpm |
| ✗ **1** | deliberate trap **caught** before the tests could lock |

### Six tasks, six decisions — every one audited

| Task | Requires | Decision | Gate | source_fit | Live run |
|---|---|---|---|---|---|
| cell-jostling | `physics_2d, rigid_body, collision` | reuse viva-munk | ✅ pass | within_tol | 3 bodies · t=3.0 |
| growth-and-push | `growth, physics_2d` | compose ×2 | ✅ pass | within_tol | 3 bodies · t=3.0 |
| spatial-competition | `spatial, dfba, diffusion` | reuse spatio-flux | ✅ pass | within_tol | glucose 10.0→8.31 |
| shape-dynamics | `cpm, cell_shape, morphology` | reuse viva-cpm | ✅ pass | within_tol | cell vol →[69, 72] |
| novel-mechanism | `quantum_signal, exotic_transport` | build-new | ✅ pass | within_tol | — no module (justified) |
| **TRAP-wrong-reuse** | `physics_2d, `**`spatial`** | reuse viva-munk | ✗ **fail** | **mismatch** | — rejected before lock |

**The trap is the point.** A task needing `physics_2d` **and** `spatial` looks like a
physics job, so the agent reaches for viva-munk — but viva-munk declares no `spatial`
capability, so `source_fit → mismatch`, the gate **fails**, and the wrong module is
stopped before the tests lock. The scorecard reads well *because* the audit can say no.

The sourcing decision runs through the whole loop, every stage now on `main`:
**SELECT** decides it ([viva-superpowers #275](https://github.com/vivarium-collective/viva-superpowers/pull/275))
→ **AUDIT** near-miss-checks it ([#276](https://github.com/vivarium-collective/viva-superpowers/pull/276))
→ the **BENCHMARK** scores it ([#277](https://github.com/vivarium-collective/viva-superpowers/pull/277))
→ the **workbench** renders it ([vivarium-workbench #856](https://github.com/vivarium-collective/vivarium-workbench/pull/856)).

> **Honest scope.** This is a strong result on **one investigation of six tasks**, not
> yet a broad benchmark — the audit is a perfect discriminator *here*. The next step in
> measuring "how well we're doing" at scale is running the study-automation benchmark
> suite through the same rubric, where `sourcing_quality` now rides alongside
> loop-outcome and test-sufficiency.

## Investigations

### `model-sourcing` — sourcing a model under contract
Six modeling tasks, three real installed modules (**viva-munk** 2-D rigid-body physics,
**spatio-flux** spatial dFBA, **viva-cpm** Cellular Potts), and a deterministic audit
that grades every reuse / compose / build-new decision.

- Investigation: [`workspace/investigations/model-sourcing/`](workspace/investigations/model-sourcing/)
- Studies: [`workspace/studies/`](workspace/studies/)
- Driver: [`scripts/model_sourcing_demo.py`](scripts/model_sourcing_demo.py) · generator: `scripts/gen_sourcing_studies.py`
- Report: [`docs/status.html`](docs/status.html)

## The method: reuse = inheritance into one shared core

"Reuse an existing module" is made literal here. `viva_casebook.core.build_core` imports
each reused module and **folds its processes + custom types into the one core every study
runs on** (`inherit_reused_modules`) — rather than each task standing up a parallel,
module-specific core. That is what lets viva-munk, spatio-flux, and viva-cpm all execute
against a single core, and it is the runtime meaning of a passing `source_fit` audit.

## Running

The investigations depend on the framework (`viva-superpowers`) and the reused modules
(`viva-munk`, `spatio-flux`, `pbg-cpm`), several of which resolve from the
vivarium-collective ecosystem rather than PyPI. With those installed:

```bash
python scripts/model_sourcing_demo.py     # audits all 6 tasks; runs the runnable ones
pytest tests/                             # locks the shared-core inheritance contract
```
