"""ShapeRelaxation — the reused viva-cpm engine relaxing two cells toward target volume.

shape-dynamics is a MODEL-SOURCING study: the audit graded reuse of viva-cpm as PASS
(source_fit within_tol) for the required capabilities [cpm, cell_shape, morphology].
This figure shows that the reuse decision was not merely audited but demonstrated: the
inherited CPMProcess actually ran. Two cells seeded as 36px blocks relax under the
Metropolis Hamiltonian toward a target volume of 80, settling at volumes [69, 72] over
6 updates as surface energy and adhesion evolve. Each settled bar sits between the 36px
seed and the 80px target — the shape is genuinely relaxing, not stuck at the seed.

Generated for the study's declared visualization. Demo data are the study's real
reported values (seed 36 -> settled [69, 72], target 80).
"""
from __future__ import annotations
import json
from process_bigraph.visualization import as_visualization


@as_visualization(
    inputs={
        'cells': 'list[string]',
        'seed': 'list[float]',
        'settled': 'list[float]',
        'target': 'float',
    },
    name='ShapeRelaxation',
    demo={'cells': ['Cell 1', 'Cell 2'],
          'seed': [36.0, 36.0],
          'settled': [69.0, 72.0],
          'target': 80.0},
)
def update_shape_relaxation(state):
    """Grouped bars of each cell's 36px seed volume vs its settled volume, with the
    target-volume line marked — reuse viva-cpm PASS, demonstrated by a real run."""
    cells = state['cells']
    seed = state['seed']
    settled = state['settled']
    target = state['target']
    traces = [
        {
            'x': cells, 'y': seed, 'type': 'bar', 'name': 'seed (36px block)',
            'marker': {'color': '#94a3b8'},
            'text': [f'{v:.0f}' for v in seed], 'textposition': 'outside',
            'hovertemplate': '%{x}<br>seed volume = %{y:.0f} px<extra></extra>',
        },
        {
            'x': cells, 'y': settled, 'type': 'bar', 'name': 'settled (6 updates)',
            'marker': {'color': '#10b981'},
            'text': [f'{v:.0f}' for v in settled], 'textposition': 'outside',
            'hovertemplate': '%{x}<br>settled volume = %{y:.0f} px<extra></extra>',
        },
    ]
    ymax = max(settled + seed + [target]) * 1.2
    layout = {
        'title': {'text': 'reuse viva-cpm — PASS: two cells relax from a 36px seed toward target volume 80'},
        'barmode': 'group',
        'shapes': [{
            'type': 'line', 'xref': 'paper', 'yref': 'y',
            'x0': 0, 'x1': 1, 'y0': target, 'y1': target,
            'line': {'dash': 'dash', 'color': '#2563eb', 'width': 2},
        }],
        'annotations': [{
            'xref': 'paper', 'yref': 'y', 'x': 0.98, 'y': target,
            'text': f'target volume = {target:.0f} px',
            'showarrow': False, 'font': {'size': 11, 'color': '#2563eb'},
            'xanchor': 'right', 'yanchor': 'bottom',
        }],
        'margin': {'l': 55, 'r': 20, 't': 60, 'b': 50},
        'xaxis': {'title': {'text': 'Cellular Potts cell'}},
        'yaxis': {'title': {'text': 'cell volume (px)'}, 'range': [0, ymax]},
        'legend': {'orientation': 'h', 'x': 0, 'y': -0.15},
    }
    return {'html': (
        '<div id="viz" style="height:400px"></div>'
        '<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>'
        '<script>Plotly.newPlot("viz",'
        + json.dumps(traces) + ',' + json.dumps(layout)
        + ', {responsive:true, displayModeBar:false});</script>'
    )}
