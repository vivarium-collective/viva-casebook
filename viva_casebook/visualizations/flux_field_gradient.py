"""FluxFieldGradient — the cell-sourced diffusion gradient the agent-authored
translator produces, versus the flat (uncoupled) field the policy left behind.

The multiscale study couples a cell-scale metabolic model (a metabolite FLUX,
mol/time) to a tissue-scale 1-D DIFFUSION FIELD (concentration, mM). The agent
recognised the two models were decoupled and AUTHORED a FluxTranslator that maps
the cell's flux onto the field's per-grid source, carrying the unit conversion
(mol/time -> mM/time, i.e. divide by compartment volume) that conserves mass
across the scale interface (F-01..F-03). Result: DONE 4/4. The deterministic
policy GAVE UP at 1/4 — 'author a translator' is not an install it can express —
so its field is never sourced and stays flat.

This figure makes the coupling undeniable: with the translator, the cell (grid
centre) sources a concentration gradient that decays with distance; without it
the field is flat at zero. Grounded in the study's REAL result (4/4 vs policy
1/4, mM field, mol/time flux, divide-by-volume conversion). study.yaml stores no
per-grid concentration array, so the coupled curve is a small illustrative
diffusion profile consistent with the stated gradient, NOT a measured export.
"""
from __future__ import annotations
import json
from process_bigraph.visualization import as_visualization


@as_visualization(
    inputs={
        'position': 'list[float]',
        'coupled': 'list[float]',
        'decoupled': 'list[float]',
    },
    name='FluxFieldGradient',
    demo={
        # 1-D grid positions relative to the secreting cell (grid site 0).
        'position': [-3.0, -2.0, -1.0, 0.0, 1.0, 2.0, 3.0],
        # Concentration (mM) with the agent's FluxTranslator: cell flux sources
        # the field, so a gradient forms and decays away from the cell.
        'coupled': [0.12, 0.35, 0.70, 1.00, 0.70, 0.35, 0.12],
        # Concentration (mM) under the deterministic policy: no translator, the
        # field is never sourced -> flat at zero (policy gave up, 1/4).
        'decoupled': [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    },
)
def update_flux_field_gradient(state):
    """1-D metabolite field (mM) across the scale interface: the agent-authored
    translator sources a decaying gradient at the cell (grid 0); the uncoupled
    policy field stays flat at the zero-source baseline."""
    pos = state['position']
    coupled = state['coupled']
    decoupled = state['decoupled']

    traces = [
        {
            'x': pos, 'y': coupled, 'type': 'scatter', 'mode': 'lines+markers',
            'fill': 'tozeroy', 'fillcolor': 'rgba(16,185,129,0.15)',
            'line': {'color': '#10b981', 'width': 2},
            'marker': {'size': 8},
            'name': 'agent: flux-coupled (4/4)',
            'hovertemplate': ('grid site %{x:.0f}<br>'
                              'concentration = %{y:.2f} mM<extra></extra>'),
        },
        {
            'x': pos, 'y': decoupled, 'type': 'scatter', 'mode': 'lines+markers',
            'line': {'color': '#94a3b8', 'width': 2, 'dash': 'dash'},
            'marker': {'size': 6},
            'name': 'policy: uncoupled (1/4)',
            'hovertemplate': ('grid site %{x:.0f}<br>'
                              'concentration = %{y:.2f} mM<extra></extra>'),
        },
    ]
    layout = {
        'title': {'text': 'The agent-authored translator couples the scales: cell flux sources a diffusion gradient'},
        'annotations': [{
            'xref': 'x', 'yref': 'y', 'x': 0.0, 'y': 1.00,
            'text': ('cell secretes flux (mol/time)<br>'
                     '→ ÷ volume → field source (mM/time), mass conserved'),
            'showarrow': True, 'arrowhead': 2, 'ax': 70, 'ay': -30,
            'font': {'size': 10, 'color': '#065f46'},
            'align': 'left',
        }],
        'margin': {'l': 60, 'r': 20, 't': 60, 'b': 50},
        'xaxis': {'title': {'text': 'grid position relative to secreting cell (lattice sites)'},
                  'dtick': 1},
        'yaxis': {'title': {'text': 'metabolite concentration (mM)'}, 'range': [0, 1.15]},
        'legend': {'orientation': 'h', 'y': -0.2},
    }
    return {'html': (
        '<div id="viz" style="height:400px"></div>'
        '<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>'
        '<script>Plotly.newPlot("viz",'
        + json.dumps(traces) + ',' + json.dumps(layout)
        + ', {responsive:true, displayModeBar:false});</script>'
    )}
