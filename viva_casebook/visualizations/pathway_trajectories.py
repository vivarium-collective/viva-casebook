"""PathwayTrajectories — A->B->C species trajectories to steady state, with the
terminal product C accumulating as the dominant species and total mass conserved.

The sbml study's agent authored an SBML kinetic model (libsbml) of the linear
mass-action pathway A->B->C, loaded and simulated in the REAL COPASI backend
(basico, via viva-copasi). It recognised after building A->B that the pathway
stopped at B and added B->C, so material flows to the terminus rather than
pooling at the intermediate: C ends dominant, total mass A+B+C is conserved, and
the run reaches a valid steady state (F-01..F-03). DONE 5/5; the deterministic
policy GAVE UP at 0/5 (authoring an SBML network is not an install).

Grounded in the study's REAL result: A->B->C mass-action, C the dominant
terminal product, mass conserved, steady state. study.yaml stores no per-time
COPASI export, so these curves are a small illustrative mass-action integration
normalised so A+B+C = 1 at every step — a shape clearly consistent with the
stated qualitative result (A decays, B is a transient intermediate, C rises to
dominance, total conserved), NOT a claimed point-by-point COPASI trajectory.
"""
from __future__ import annotations
import json
from process_bigraph.visualization import as_visualization


@as_visualization(
    inputs={
        'time': 'list[float]',
        'A': 'list[float]',
        'B': 'list[float]',
        'C': 'list[float]',
        'total': 'float',
    },
    name='PathwayTrajectories',
    demo={
        'time': [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0],
        # Substrate A decays as it is consumed by A->B.
        'A': [1.000, 0.607, 0.368, 0.223, 0.135, 0.082, 0.050, 0.018, 0.007],
        # Intermediate B is transient: rises, then drained by B->C.
        'B': [0.000, 0.300, 0.420, 0.400, 0.330, 0.250, 0.180, 0.090, 0.045],
        # Terminal product C accumulates to dominance.
        'C': [0.000, 0.093, 0.212, 0.377, 0.535, 0.668, 0.770, 0.892, 0.948],
        'total': 1.0,
    },
)
def update_pathway_trajectories(state):
    """A, B, C amounts vs time for the mass-action A->B->C pathway; the conserved
    total (A+B+C) is drawn as a reference line, and C reaches dominance at the
    terminal steady state."""
    t = state['time']
    A, B, C = state['A'], state['B'], state['C']
    total = state['total']

    def _trace(y, name, color):
        return {
            'x': t, 'y': y, 'type': 'scatter', 'mode': 'lines+markers',
            'line': {'color': color, 'width': 2.5}, 'marker': {'size': 6},
            'name': name,
            'hovertemplate': name + '<br>t = %{x:.0f}<br>amount = %{y:.3f}<extra></extra>',
        }

    traces = [
        _trace(A, 'A (substrate)', '#f59e0b'),
        _trace(B, 'B (intermediate)', '#6366f1'),
        _trace(C, 'C (terminal product)', '#10b981'),
    ]
    layout = {
        'title': {'text': 'A→B→C reaches steady state: terminal product C dominates, total mass conserved'},
        'shapes': [{
            'type': 'line', 'xref': 'paper', 'yref': 'y',
            'x0': 0, 'x1': 1, 'y0': total, 'y1': total,
            'line': {'dash': 'dash', 'color': '#f43f5e', 'width': 1},
        }],
        'annotations': [{
            'xref': 'paper', 'yref': 'y', 'x': 0.01, 'y': total,
            'text': f'conserved total A+B+C = {total:.2f}',
            'showarrow': False, 'font': {'size': 11, 'color': '#be123c'},
            'xanchor': 'left', 'yanchor': 'bottom',
        }],
        'margin': {'l': 55, 'r': 20, 't': 60, 'b': 50},
        'xaxis': {'title': {'text': 'simulation time (a.u.)'}},
        'yaxis': {'title': {'text': 'species amount (normalised, total = 1)'},
                  'range': [0, total * 1.1]},
        'legend': {'orientation': 'h', 'y': -0.2},
    }
    return {'html': (
        '<div id="viz" style="height:400px"></div>'
        '<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>'
        '<script>Plotly.newPlot("viz",'
        + json.dumps(traces) + ',' + json.dumps(layout)
        + ', {responsive:true, displayModeBar:false});</script>'
    )}
