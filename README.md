# viva-casebook

A **casebook of capability-testing investigations** for the vivarium model-building
framework — studies whose object of evaluation is *the framework's own ability to
build models well*, kept separate from any single paper or model.

The framework itself lives in
[viva-superpowers](https://github.com/vivarium-collective/viva-superpowers)
(`loop_state`, `module_sourcing`, `test_audit`, `benchmark_score`, and the
`/viva-model-build` · `/viva-audit-tests` · `/viva-benchmark` skills). This repo
holds the **investigations that exercise it** on real modules and render the
evidence.

## Investigations

### `model-sourcing` — sourcing a model under contract
Six modeling tasks, three real installed modules (**viva-munk** 2-D rigid-body
physics, **spatio-flux** spatial dFBA, **viva-cpm** Cellular Potts), and a
deterministic audit that grades every **reuse / compose / build-new** decision —
including a trap where a plausible-but-wrong module is caught before the tests
lock. All three reused modules run live on **one shared workspace core**.

- Investigation: [`workspace/investigations/model-sourcing/`](workspace/investigations/model-sourcing/)
- Studies: [`workspace/studies/`](workspace/studies/)
- Driver: [`scripts/model_sourcing_demo.py`](scripts/model_sourcing_demo.py) · generator: `scripts/gen_sourcing_studies.py`
- Report: [`docs/model-sourcing-under-contract.html`](docs/model-sourcing-under-contract.html)

## The method: reuse = inheritance into one shared core

"Reuse an existing module" is made literal here. `viva_casebook.core.build_core`
imports each reused module and **folds its processes + custom types into the one
core every study runs on** (`inherit_reused_modules`) — rather than each task
standing up a parallel, module-specific core. That is what lets viva-munk,
spatio-flux, and viva-cpm all execute against a single core, and it is the
runtime meaning of a passing `source_fit` audit.

## Running

The investigations depend on the framework (`viva-superpowers`) and the reused
modules (`viva-munk`, `spatio-flux`, `pbg-cpm`), several of which resolve from the
vivarium-collective ecosystem rather than PyPI. With those installed:

```bash
python scripts/model_sourcing_demo.py     # audits all 6 tasks; runs the runnable ones
pytest tests/                             # locks the shared-core inheritance contract
```
