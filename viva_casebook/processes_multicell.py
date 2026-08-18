"""Subcellular fate model for a multicellular differentiation phenotype.

A per-cell fate rule wired to the CPM engine: it reads each cell's locally-sensed
morphogen (`field_at_cell`, e.g. Wnt) and the current cell `types`, computes a
stemness via a Hill response, and writes a `fates` map the CPM consumes to
relabel cells. Progenitor cells near the secreting niche see high morphogen and
stay stem; distal cells see low morphogen and differentiate — a spatial
differentiation GRADIENT, the multicellular phenotype.

This is the crypt's subcellular logic (stemness → fate) without the SBML/
tellurium dependency, so it runs anywhere the CPM engine does.
"""
from __future__ import annotations

from process_bigraph import Process


class StemnessFate(Process):
    config_schema = {
        "wnt_threshold": {"_type": "float", "_default": 20.0},
        "hill_n": {"_type": "float", "_default": 4.0},
        "source_type": {"_type": "integer", "_default": 1},   # the niche — never differentiates
        "stem_type": {"_type": "integer", "_default": 2},      # progenitor stays stem (high Wnt)
        "diff_type": {"_type": "integer", "_default": 3},      # progenitor differentiates (low Wnt)
    }

    def inputs(self):
        # read the current fates too, so we can emit OVERWRITE deltas (the CPM
        # fates map applies additively; emitting target−current lands on target).
        return {"field_at_cell": "map[float]", "types": "list", "fates": "map[integer]"}

    def outputs(self):
        return {"fates": "map[integer]"}

    def update(self, state, interval):
        fac = state.get("field_at_cell") or {}
        types = state.get("types") or []
        cur = state.get("fates") or {}
        c = self.config
        thr, n = c["wnt_threshold"], c["hill_n"]
        out = {}
        for cid_str, wnt in fac.items():
            cid = int(cid_str)
            t = types[cid] if 0 <= cid < len(types) else 0
            if t == c["source_type"] or t == 0:
                continue                                   # niche + medium untouched
            # stemness = Hill(Wnt); above threshold → stay stem, below → differentiate
            stemness = (wnt ** n) / (thr ** n + wnt ** n) if wnt > 0 else 0.0
            target = c["stem_type"] if stemness >= 0.5 else c["diff_type"]
            out[cid_str] = target - int(cur.get(cid_str, 0))   # overwrite delta
        return {"fates": out}
