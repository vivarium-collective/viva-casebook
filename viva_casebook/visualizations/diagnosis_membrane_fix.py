"""DiagnosisMembraneFix — biomass & viability before vs after stabilize_membrane.

The diagnosis study's finding (gate passed 2/2, DONE in 1 edit) is that low
biomass was caused by the cell DYING, not by broken yield or uptake — a cause
readable only from the JOINT observables (nutrient fully consumed, so uptake is
fine; viability crashed, so the cell is dying). The one correct fix,
stabilize_membrane, arrests the MembraneStress viability decay and lifts the
cell over BOTH acceptance thresholds: biomass >= 3.0 and viability >= 0.5.

This grouped comparison makes that undeniable: before the fix, both bars sit
below their threshold lines (fails both tests); after stabilize_membrane, both
clear their thresholds (passes both).

Honesty note: the acceptance thresholds — biomass >= 3.0 and viability >= 0.5 —
are the study's real reported targets, and the direction (before fails both /
after passes both) is the confirmed result. The specific before/after bar
heights are an illustrative shape keyed to those real thresholds; the study
reports the pass/fail outcome and the qualitative crash, not raw values.

Generated for the agentic-challenges investigation.
"""
from __future__ import annotations
import json
from process_bigraph.visualization import as_visualization


@as_visualization(
    inputs={
        'conditions': 'list[string]',
        'biomass': 'list[float]',
        'viability': 'list[float]',
        'biomass_target': 'float',
        'viability_threshold': 'float',
    },
    name='DiagnosisMembraneFix',
    demo={
        'conditions': ['Before (dying cell)', 'After stabilize_membrane'],
        # Before: far below the 3.0 target; after: clears it.
        'biomass': [0.9, 3.2],
        # Before: viability crashed; after: held above the 0.5 survival threshold.
        'viability': [0.05, 0.62],
        'biomass_target': 3.0,
        'viability_threshold': 0.5,
    },
)
def update_diagnosis_membrane_fix(state):
    """Grouped bars of biomass (left axis, target 3.0) and viability (right axis,
    threshold 0.5) before and after the stabilize_membrane fix."""
    conditions = state['conditions']
    biomass = state['biomass']
    viability = state['viability']
    b_target = state['biomass_target']
    v_thresh = state['viability_threshold']

    traces = [
        {
            'x': conditions, 'y': biomass, 'type': 'bar',
            'name': 'biomass',
            'marker': {'color': ['#cbd5e1', '#10b981']},
            'text': [f'{v:.2f}' for v in biomass], 'textposition': 'outside',
            'yaxis': 'y',
            'hovertemplate': '%{x}<br>biomass = %{y:.2f} a.u. (target ≥ 3.0)<extra></extra>',
        },
        {
            'x': conditions, 'y': viability, 'type': 'bar',
            'name': 'viability',
            'marker': {'color': ['#fca5a5', '#6366f1']},
            'text': [f'{v:.2f}' for v in viability], 'textposition': 'outside',
            'yaxis': 'y2',
            'hovertemplate': '%{x}<br>viability = %{y:.2f} (threshold ≥ 0.5)<extra></extra>',
        },
    ]
    layout = {
        'title': {'text': 'stabilize_membrane fixes a DYING cell: biomass ≥ 3.0 and viability ≥ 0.5 both cleared'},
        'barmode': 'group',
        'shapes': [
            {
                'type': 'line', 'xref': 'paper', 'yref': 'y',
                'x0': 0, 'x1': 1, 'y0': b_target, 'y1': b_target,
                'line': {'dash': 'dash', 'color': '#10b981', 'width': 1.5},
            },
            {
                'type': 'line', 'xref': 'paper', 'yref': 'y2',
                'x0': 0, 'x1': 1, 'y0': v_thresh, 'y1': v_thresh,
                'line': {'dash': 'dash', 'color': '#6366f1', 'width': 1.5},
            },
        ],
        'annotations': [
            {
                'xref': 'paper', 'yref': 'y', 'x': 0.02, 'y': b_target,
                'text': f'biomass target = {b_target:.1f}',
                'showarrow': False, 'font': {'size': 10, 'color': '#10b981'},
                'xanchor': 'left', 'yanchor': 'bottom',
            },
            {
                'xref': 'paper', 'yref': 'y2', 'x': 0.98, 'y': v_thresh,
                'text': f'viability threshold = {v_thresh:.1f}',
                'showarrow': False, 'font': {'size': 10, 'color': '#6366f1'},
                'xanchor': 'right', 'yanchor': 'bottom',
            },
        ],
        'legend': {'orientation': 'h', 'x': 0.5, 'y': -0.15, 'xanchor': 'center'},
        'margin': {'l': 60, 'r': 60, 't': 60, 'b': 50},
        'xaxis': {'title': {'text': 'model condition'}},
        'yaxis': {'title': {'text': 'biomass (a.u.)'}, 'range': [0, max(biomass + [b_target]) * 1.25], 'color': '#10b981'},
        'yaxis2': {
            'title': {'text': 'viability (fraction)'}, 'range': [0, 1.0],
            'overlaying': 'y', 'side': 'right', 'color': '#6366f1',
        },
    }
    return {'html': (
        '<div id="viz" style="height:420px"></div>'
        '<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>'
        '<script>Plotly.newPlot("viz",'
        + json.dumps(traces) + ',' + json.dumps(layout)
        + ', {responsive:true, displayModeBar:false});</script>'
    )}
