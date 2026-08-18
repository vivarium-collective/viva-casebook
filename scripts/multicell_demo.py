"""Multicellular + subcellular differentiation phenotype — the real composite.

The foundation for casebook task #5: an agent must SELECT a multicellular
simulator (here the CPM engine is the right one for a lattice/field/fate
phenotype), then wire a SUBCELLULAR fate model into the cells to produce a
tissue-scale phenotype — a spatial differentiation GRADIENT.

Composite: a Wnt-secreting niche (type 1) + a row of progenitor cells (type 2)
on the CPM lattice, a diffusing Wnt field, and a `StemnessFate` subcell that
reads each cell's locally-sensed Wnt and sets its fate (stem near the niche,
differentiated distally). Runs through the real engine; prints the phenotype.

Three pbg gotchas this encodes: the reaction-diffusion field is unstable for
d>0.25 (blows up); the CPM `fates` map drops writes to un-pre-initialised keys
(so the store is seeded per cell); and `map[integer]` applies additively, so the
subcell emits OVERWRITE deltas (target−current).
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import viva_casebook.core as _vc_core
from process_bigraph import Composite

DT = 1.0


def _node(a, cfg, i, o):
    return {"_type": "process", "address": "local:" + a, "config": cfg, "inputs": i, "outputs": o, "interval": DT}


def build(*, wnt_d=0.2, wnt_decay=0.01, wnt_rate=3.0, wnt_threshold=0.3):
    cells = [{"type": 1, "target_volume": 36.0, "lambda_volume": 2.0, "target_surface": 28.0,
              "lambda_surface": 0.5, "seed_block": [2, 18, 0, 8, 24, 1]}]           # niche
    for x in range(12, 40, 7):                                                       # progenitors, increasing distance
        cells.append({"type": 2, "target_volume": 30.0, "lambda_volume": 2.0, "target_surface": 26.0,
                      "lambda_surface": 0.5, "seed_block": [x, 18, 0, x + 5, 24, 1]})
    spec = {"potts": {"dims": [44, 44, 1], "boundary": "noflux", "neighbor_order": 2, "temperature": 8.0, "seed": 1},
            "cells": cells,
            "contact": [{"a": a, "b": b, "j": 8.0} for a in (1, 2, 3) for b in (1, 2, 3) if a <= b],
            "fields": [{"name": "Wnt", "d": wnt_d, "decay": wnt_decay,
                        "secretion": [{"type": 1, "rate": wnt_rate}], "chemotaxis": []}]}
    prog_ids = {str(i) for i in range(2, len(cells) + 1)}
    state = {
        "cpm": _node("CPMProcess", {"spec": spec, "mcs_per_update": 6, "n_fields": 1, "secretory_types": [1]},
                     {"fates": ["fates"]},
                     {"volumes": ["volumes"], "types": ["types"], "positions": ["positions"],
                      "field_at_cell": ["field_at_cell"], "neighbor_secretory": ["neighbor_secretory"]}),
        "fate": _node("StemnessFate", {"wnt_threshold": wnt_threshold, "hill_n": 4.0,
                      "source_type": 1, "stem_type": 2, "diff_type": 3},
                      {"field_at_cell": ["field_at_cell"], "types": ["types"], "fates": ["fates"]},
                      {"fates": ["fates"]}),
        "fates": {cid: 0 for cid in prog_ids},               # pre-init per cell so per-key writes land
        "volumes": [], "types": [], "positions": [], "field_at_cell": {}, "neighbor_secretory": {},
    }
    return state


def phenotype(sim):
    types = sim.state.get("types") or []
    pos = sim.state.get("positions") or []
    src = [np.array(p[:2]) for i, p in enumerate(pos) if i < len(types) and types[i] == 1]
    prog = sorted((min(float(np.linalg.norm(np.array(pos[i][:2]) - s)) for s in src), types[i])
                  for i in range(len(types)) if types[i] in (2, 3))
    if not prog:
        return prog, False
    mid = prog[len(prog) // 2][0]
    near = [t for d, t in prog if d < mid]
    far = [t for d, t in prog if d >= mid]
    achieved = bool(near) and bool(far) and all(t == 2 for t in near) and all(t == 3 for t in far)
    return prog, achieved


def main():
    core = _vc_core.build_core()
    sim = Composite({"state": build()}, core=core)
    sim.run(24)
    prog, achieved = phenotype(sim)
    print("Multicellular + subcellular differentiation phenotype (CPM + Wnt field + StemnessFate subcell):")
    print("  cell types:", sim.state.get("types"), " (0=medium 1=niche 2=stem 3=differentiated)")
    print("  progenitors (distance → fate):", [(round(d, 1), "STEM" if t == 2 else "DIFF") for d, t in prog])
    print(f"  GRADIENT PHENOTYPE achieved: {achieved}")


if __name__ == "__main__":
    main()
