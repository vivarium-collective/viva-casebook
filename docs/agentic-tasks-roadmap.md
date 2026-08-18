# Hard agentic-modeling tasks — a benchmark roadmap

The point of viva-casebook is to find modeling tasks that a **deterministic policy
cannot solve** but an **LLM agent can** — because the fix requires reasoning a
hill-climber has no access to. Each task below isolates one such capability, is
(or will be) a real process-bigraph composite, and is graded by locked tests with
a head-to-head LLM-vs-policy comparison.

The discriminating property: for each task, the policy's action vocabulary
(install the mechanism a failing test *names* / step a knob by the sign of its
margin) has **no move** for the real fix.

> ## ⚠️ Fair-baseline caveat (added 2026-08-18, from Fable's review)
>
> The "policy has no move" framing above is only honest against a **naive-map**
> policy whose action map is hand-authored to *omit* the winning mechanism. A
> fairer control — a **brute-force enumerating policy** that installs any
> uninstalled library mechanism when stuck (`scripts/enumerating_baseline.py`,
> run for real) — **solves all three small-library menu tasks in 3 edits each**,
> because the winning mechanism is one of the ≤3 items in the library:
>
> ```
> diauxie:   DONE in 3 edits (library of 3)
> diagnosis: DONE in 3 edits (library of 3)
> bistable:  DONE in 3 edits (library of 3)
> ```
>
> So for tasks **2–4** the demonstration shows the LLM reasons *efficiently* (it
> installs only the needed mechanism, without wasted edits) — **not** that an
> agent is *required*; a dumb enumerator also reaches DONE. The "genuinely requires
> an agent" thesis only holds where the real fix cannot be expressed as "install a
> library item," and tasks **5–7** are themselves still small curated menus in the
> current code. Making the necessity claim real needs the follow-on work: an
> **open action space**, **live logged agent runs** (not replayed transcripts), and
> **data-grounded tests**. Until then, read the head-to-heads as *efficiency and
> reasoning-quality* comparisons on a shared substrate, not proof of necessity.

| # | Task | Capability it uniquely requires | Real tooling | Feasibility | Status |
|---|---|---|---|---|---|
| 1 | **Bounded cell** | quantitative single-shot calibration | pbg composites | ready | ✅ done (LLM 4 edits vs policy 5) |
| 2 | **Diauxie** (glucose→lactose) | **regulatory reasoning** — the fix is a *coupling* (catabolite repression), not a knob or named mechanism | pbg composites | ready | ✅ done (**policy GIVE_UP 3/4, LLM DONE 4/4**) |
| 3 | **Ambiguous diagnosis** ("biomass too low") | **diagnose** the cause from *joint* observables; worst single margin points at the wrong fix | pbg composites | **built** | **DONE** — policy misdiagnoses (boost_yield) → GIVE_UP; LLM reads joint observables → DONE 1 edit |
| 4 | **Bistable toggle switch** | **discover a topology** (mutual repression) + a narrow bistable regime — unreachable by knob-stepping | pbg composites | **built** | **DONE** — policy tunes expression, stays monostable → GIVE_UP; LLM adds cooperative feedback (Hill n≥2) → DONE 1 edit |
| 5 | **Multicellular + subcellular phenotype** | **SELECT a multicellular simulator** (CPM vs rigid-body vs spatial), then compose subcellular models to hit a tissue phenotype | `viva-cpm`, `viva-munk`, `spatio-flux` | **built** | ✅ done (**policy GIVE_UP, LLM DONE** — selects CPM, composes subcell fate) |
| 6 | **Multiscale coupling via a translator** | author a **typed translator** that couples two models at different scales (units/variables/timescale) | `spatio-flux` precedent; see `project_domain_bridges_formalization` | **built** | ✅ done (**policy GIVE_UP 1/4, LLM DONE 4/4** — authors translator + unit conversion) |
| 7 | **Build complex SBML → COPASI → test quality** | author a large **SBML** model + validate it through an **external tool** (round-trip, steady-state, conservation) | **viva-copasi** wrapper (`basico`/COPASI) installed; `libsbml` present | **built** | ✅ done (**policy GIVE_UP 0/5, LLM DONE 5/5** — real COPASI validation) |

## Notes on the hardest two
- **#7 (SBML/COPASI)** is the largest: it needs a `viva-copasi` package (a COPASI
  wrapper, likely over `basico`) before the agent task can run. That wrapper is
  itself a worthwhile ecosystem piece. Quality tests = SBML round-trips cleanly,
  COPASI reaches the expected steady state, conservation laws hold, and the model
  reproduces a reference time-course.
- **#6 (translator)** is where an LLM's value is starkest: coupling e.g. a
  genome-scale FBA model to a spatial diffusion field requires inventing the
  *interface* (which fluxes map to which field sources, unit conversions, the
  update cadence) — a policy has no representation for "author a translator".

## Build order (recommended)
Ready-and-impressive first, tooling-heavy last: **#5 multicellular → #6 translator
→ #3 diagnosis → #4 bistability → #7 SBML/COPASI** (build the `viva-copasi`
wrapper as its own step before #7).
