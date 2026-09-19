"""DifferentiationGradient — cell fate vs distance from the Wnt-secreting niche
on the CPM (viva-cpm) lattice.

The multicellular study's phenotype is spatial: a diffusing Wnt field emanates
from a secreting niche, and a StemnessFate subcell in each cell reads its LOCAL
Wnt level to set fate. Cells near the niche see high Wnt and stay STEM; distal
cells see low Wnt and become DIFFERENTIATED — a spatial differentiation gradient
over a tissue of >=4 cells (F-02, F-03). This figure makes that undeniable: the
Wnt gradient decays with distance, and the StemnessFate threshold cleanly splits
the near cells (STEM) from the far cells (DIFFERENTIATED).

Grounded in the study's REAL qualitative result: >=4 cells on the CPM lattice,
a diffusing Wnt field from the niche, StemnessFate reading local Wnt, near STEM /
far DIFFERENTIATED. study.yaml stores no per-cell Wnt time-series, so the decay
curve is a small illustrative shape clearly consistent with that stated result
(monotonic Wnt decay + one threshold), NOT a claimed measured trajectory.
"""
from __future__ import annotations
import json
from process_bigraph.visualization import as_visualization


@as_visualization(
    inputs={
        'distance': 'list[float]',
        'wnt': 'list[float]',
        'fate': 'list[string]',
        'threshold': 'float',
    },
    name='DifferentiationGradient',
    demo={
        # >=4 cells at increasing lattice distance from the Wnt-secreting niche.
        'distance': [1.0, 2.0, 3.0, 4.0],
        # Local Wnt seen by each cell — decays away from the niche (illustrative
        # shape consistent with a diffusing field sourced at the niche).
        'wnt': [0.90, 0.55, 0.25, 0.08],
        # Fate set by the StemnessFate subcell from local Wnt vs the threshold.
        'fate': ['STEM', 'STEM', 'DIFFERENTIATED', 'DIFFERENTIATED'],
        'threshold': 0.40,
    },
)
def update_differentiation_gradient(state):
    """Local Wnt vs distance from the niche, with each cell coloured by the fate
    the StemnessFate subcell assigns; the fate threshold is drawn as a reference
    line (Wnt above => STEM, below => DIFFERENTIATED)."""
    dist = state['distance']
    wnt = state['wnt']
    fate = state['fate']
    thr = state['threshold']

    stem_x = [d for d, f in zip(dist, fate) if f == 'STEM']
    stem_y = [w for w, f in zip(wnt, fate) if f == 'STEM']
    diff_x = [d for d, f in zip(dist, fate) if f == 'DIFFERENTIATED']
    diff_y = [w for w, f in zip(wnt, fate) if f == 'DIFFERENTIATED']

    traces = [
        {  # the underlying Wnt gradient
            'x': dist, 'y': wnt, 'type': 'scatter', 'mode': 'lines',
            'line': {'color': '#cbd5e1', 'width': 2, 'dash': 'dot'},
            'name': 'local Wnt (field)', 'hoverinfo': 'skip',
        },
        {  # cells that stayed STEM (near the niche)
            'x': stem_x, 'y': stem_y, 'type': 'scatter', 'mode': 'markers',
            'marker': {'color': '#10b981', 'size': 16,
                       'line': {'color': '#065f46', 'width': 1}},
            'name': 'STEM (near niche)',
            'hovertemplate': ('cell at distance %{x:.0f}<br>'
                              'local Wnt = %{y:.2f}<br>fate = STEM<extra></extra>'),
        },
        {  # cells that differentiated (distal)
            'x': diff_x, 'y': diff_y, 'type': 'scatter', 'mode': 'markers',
            'marker': {'color': '#6366f1', 'size': 16, 'symbol': 'square',
                       'line': {'color': '#3730a3', 'width': 1}},
            'name': 'DIFFERENTIATED (distal)',
            'hovertemplate': ('cell at distance %{x:.0f}<br>'
                              'local Wnt = %{y:.2f}<br>fate = DIFFERENTIATED<extra></extra>'),
        },
    ]
    layout = {
        'title': {'text': 'Near the niche cells stay STEM; distal cells DIFFERENTIATE down the Wnt gradient'},
        'shapes': [{
            'type': 'line', 'xref': 'paper', 'yref': 'y',
            'x0': 0, 'x1': 1, 'y0': thr, 'y1': thr,
            'line': {'dash': 'dash', 'color': '#f43f5e', 'width': 1},
        }],
        'annotations': [{
            'xref': 'paper', 'yref': 'y', 'x': 0.01, 'y': thr,
            'text': f'StemnessFate threshold (Wnt = {thr:.2f})',
            'showarrow': False, 'font': {'size': 11, 'color': '#be123c'},
            'xanchor': 'left', 'yanchor': 'bottom',
        }],
        'margin': {'l': 60, 'r': 20, 't': 60, 'b': 50},
        'xaxis': {'title': {'text': 'distance from Wnt-secreting niche (lattice sites)'},
                  'dtick': 1},
        'yaxis': {'title': {'text': 'local Wnt concentration (a.u.)'}, 'range': [0, 1.0]},
        'legend': {'orientation': 'h', 'y': -0.2},
    }
    return {'html': (
        '<div id="viz" style="height:400px"></div>'
        '<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>'
        '<script>Plotly.newPlot("viz",'
        + json.dumps(traces) + ',' + json.dumps(layout)
        + ', {responsive:true, displayModeBar:false});</script>'
    )}
