"""Multiscale coupling via a translator — two models at different scales.

Model A (cell scale): a cell that grows and secretes a metabolite, producing a
scalar FLUX (mol · time⁻¹). Model B (tissue scale): a 1-D diffusion FIELD of that
metabolite (concentration, mM, on a grid) with a per-grid `source` input. The two
run in different variables and units and DO NOT couple on their own.

The TRANSLATOR is the interface an agent must author: it maps the cell's scalar
flux to the field's per-grid source term at the cell's location — which requires
a unit conversion (mol·time⁻¹ → mM·time⁻¹, i.e. divide by the compartment volume)
and a spatial placement. Without it the field has no source and stays flat; a
naive translator that forgets the unit conversion breaks flux conservation.
"""
from __future__ import annotations

from process_bigraph import Process


def _f(default):
    return {"_type": "float", "_default": default}


class CellMetabolism(Process):
    """Model A: cell grows and secretes a metabolite → a scalar flux (mol/time)."""
    config_schema = {"k_grow": _f(0.2), "k_secrete": _f(0.5), "volume": _f(1.0)}

    def inputs(self):
        return {"biomass": "float", "secretion_flux": "float"}

    def outputs(self):
        return {"biomass": "float", "secretion_flux": "float"}

    def update(self, state, interval):
        X = float(state.get("biomass", 0.0))
        c = self.config
        flux = c["k_secrete"] * X                      # mol · time⁻¹
        return {"biomass": c["k_grow"] * X * interval,
                "secretion_flux": flux - float(state.get("secretion_flux", 0.0))}   # overwrite


class DiffusionField(Process):
    """Model B: 1-D reaction-diffusion field with a per-grid source input."""
    config_schema = {"D": _f(0.3), "decay": _f(0.02)}

    def inputs(self):
        return {"field": "list", "field_source": "list"}

    def outputs(self):
        return {"field": "overwrite[list]"}

    def update(self, state, interval):
        f = [float(x) for x in (state.get("field") or [])]
        src = [float(x) for x in (state.get("field_source") or [])]
        n = len(f)
        if n == 0:
            return {"field": f}
        D, decay = self.config["D"], self.config["decay"]
        out = []
        for i in range(n):
            left = f[i - 1] if i > 0 else f[0]          # no-flux boundary
            right = f[i + 1] if i < n - 1 else f[n - 1]
            lap = left - 2 * f[i] + right
            s = src[i] if i < len(src) else 0.0
            out.append(max(0.0, f[i] + (D * lap + s - decay * f[i]) * interval))
        return {"field": out}


class FluxTranslator(Process):
    """The TRANSLATOR: cell flux (mol/time) → field source (mM/time) at the cell's
    grid position, with the unit conversion (÷ volume) that makes the two scales
    consistent. `apply_unit_conversion=False` is the naive version that breaks
    flux conservation."""
    config_schema = {"grid_n": {"_type": "integer", "_default": 11},
                     "cell_position": {"_type": "integer", "_default": 5},
                     "volume": _f(1.0),
                     "apply_unit_conversion": {"_type": "boolean", "_default": True}}

    def inputs(self):
        return {"secretion_flux": "float"}

    def outputs(self):
        return {"field_source": "overwrite[list]"}

    def update(self, state, interval):
        flux = float(state.get("secretion_flux", 0.0))
        c = self.config
        n, pos = int(c["grid_n"]), int(c["cell_position"])
        src = [0.0] * n
        rate = flux / c["volume"] if c["apply_unit_conversion"] else flux   # mol/time → mM/time
        if 0 <= pos < n:
            src[pos] = rate
        return {"field_source": src}
