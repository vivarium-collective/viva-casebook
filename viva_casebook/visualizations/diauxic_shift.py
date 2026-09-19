"""DiauxicShift — sequential glucose-then-lactose consumption with the switch.

The diauxie study's confirmed phenotype (gate passed 4/4) is DIAUXIC growth:
the cell consumes glucose FIRST and only switches to lactose once glucose is
EXHAUSTED — a sequential shift, not simultaneous co-consumption. The mechanism
is CataboliteRepression: a Hill switch driven by glucose gates LactoseUptake
through a lac_repression store, holding lactose uptake OFF while glucose remains
and lifting it once glucose runs out.

This time course makes the ordering undeniable: glucose falls to zero first,
lactose stays flat (repressed) until the marked diauxic switch, then falls;
biomass grows in two phases with a short lag at the switch. The lac_repression
trace shows the Hill switch releasing exactly when glucose is exhausted.

Honesty note: the sequential ordering, the catabolite-repression gating, and
growth on BOTH substrates are the study's confirmed results (tests
'glucose-consumed', 'lactose-consumed', 'growth', 'diauxic-order' == within_tol,
4/4). The per-point trajectory is an illustrative shape faithful to that
qualitative phenotype; the study reports the pass outcome, not a raw time series.

Generated for the agentic-challenges investigation.
"""
from __future__ import annotations
import json
from process_bigraph.visualization import as_visualization


@as_visualization(
    inputs={
        'time': 'list[float]',
        'glucose': 'list[float]',
        'lactose': 'list[float]',
        'biomass': 'list[float]',
        'lac_repression': 'list[float]',
        'switch_time': 'float',
    },
    name='DiauxicShift',
    demo={
        'time': [0, 2, 4, 6, 8, 9, 10, 12, 14, 16, 18, 20],
        # Glucose consumed first, exhausted at the switch (t≈9).
        'glucose': [10.0, 7.6, 5.0, 2.4, 0.4, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        # Lactose held flat (repressed) until glucose is gone, then drawn down.
        'lactose': [8.0, 8.0, 8.0, 8.0, 8.0, 7.8, 6.9, 5.0, 3.2, 1.6, 0.4, 0.0],
        # Biomass grows in two phases with a short diauxic lag at the switch.
        'biomass': [0.20, 0.60, 1.15, 1.75, 2.30, 2.35, 2.45, 2.95, 3.45, 3.85, 4.10, 4.20],
        # Catabolite repression: ON (~1) while glucose remains, lifts at switch.
        'lac_repression': [1.0, 1.0, 1.0, 1.0, 0.9, 0.5, 0.2, 0.05, 0.0, 0.0, 0.0, 0.0],
        'switch_time': 9.0,
    },
)
def update_diauxic_shift(state):
    """Glucose, lactose and biomass time courses (left axis) plus catabolite
    repression (right axis), with the diauxic switch marked."""
    t = state['time']
    glucose = state['glucose']
    lactose = state['lactose']
    biomass = state['biomass']
    repression = state['lac_repression']
    switch = state['switch_time']

    traces = [
        {
            'x': t, 'y': glucose, 'type': 'scatter', 'mode': 'lines+markers',
            'name': 'glucose', 'line': {'color': '#f59e0b', 'width': 3},
            'yaxis': 'y',
            'hovertemplate': 't = %{x}<br>glucose = %{y:.2f} a.u.<extra></extra>',
        },
        {
            'x': t, 'y': lactose, 'type': 'scatter', 'mode': 'lines+markers',
            'name': 'lactose', 'line': {'color': '#3b82f6', 'width': 3},
            'yaxis': 'y',
            'hovertemplate': 't = %{x}<br>lactose = %{y:.2f} a.u.<extra></extra>',
        },
        {
            'x': t, 'y': biomass, 'type': 'scatter', 'mode': 'lines+markers',
            'name': 'biomass', 'line': {'color': '#10b981', 'width': 3},
            'yaxis': 'y',
            'hovertemplate': 't = %{x}<br>biomass = %{y:.2f} a.u.<extra></extra>',
        },
        {
            'x': t, 'y': repression, 'type': 'scatter', 'mode': 'lines',
            'name': 'lac_repression (Hill switch)',
            'line': {'color': '#94a3b8', 'width': 2, 'dash': 'dot'},
            'yaxis': 'y2',
            'hovertemplate': 't = %{x}<br>lac_repression = %{y:.2f}<extra></extra>',
        },
    ]
    layout = {
        'title': {'text': 'Diauxic shift: glucose first, then lactose — catabolite repression enforces the order'},
        'shapes': [{
            'type': 'line', 'xref': 'x', 'yref': 'paper',
            'x0': switch, 'x1': switch, 'y0': 0, 'y1': 1,
            'line': {'dash': 'dash', 'color': '#f43f5e', 'width': 2},
        }],
        'annotations': [{
            'xref': 'x', 'yref': 'paper', 'x': switch, 'y': 1.02,
            'text': 'diauxic switch: glucose exhausted → repression lifts',
            'showarrow': False, 'font': {'size': 11, 'color': '#f43f5e'},
            'xanchor': 'center', 'yanchor': 'bottom',
        }],
        'legend': {'orientation': 'h', 'x': 0.5, 'y': -0.2, 'xanchor': 'center'},
        'margin': {'l': 60, 'r': 60, 't': 60, 'b': 60},
        'xaxis': {'title': {'text': 'time (a.u.)'}},
        'yaxis': {'title': {'text': 'substrate / biomass (a.u.)'}, 'range': [0, 11]},
        'yaxis2': {
            'title': {'text': 'lac_repression (fraction)'}, 'range': [0, 1.08],
            'overlaying': 'y', 'side': 'right', 'color': '#94a3b8',
        },
    }
    return {'html': (
        '<div id="viz" style="height:440px"></div>'
        '<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>'
        '<script>Plotly.newPlot("viz",'
        + json.dumps(traces) + ',' + json.dumps(layout)
        + ', {responsive:true, displayModeBar:false});</script>'
    )}
