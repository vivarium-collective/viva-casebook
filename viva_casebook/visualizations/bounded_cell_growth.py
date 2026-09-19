"""BoundedCellGrowth — bounded growth against the thermal viability cliff.

The bounded-cell study's confirmed phenotype (gate passed, 3/3 mechanism
findings) is: biomass grows on the nutrient it consumes with Monod-SATURATING
uptake (rises then plateaus, not unbounded), while viability HOLDS below the
cell's temperature tolerance and then COLLAPSES once temperature exceeds it. The
ThermalDeath process sets that tolerance at t_tol=43 °C.

This figure plots both against a rising temperature ramp so the cliff is
undeniable: biomass saturates (bounded growth) and viability falls off a cliff
exactly at the t_tol=43 °C reference line.

Honesty note: t_tol=43 °C is the study's real reported parameter, and the
Monod-saturating-growth / viability-cliff shapes are the study's confirmed
qualitative phenotype (behavior tests 'growth', 'saturation', 'viability-cliff'
== within_tol). The per-point trajectory values are an illustrative shape keyed
to that real threshold — the study reports no raw time series.

Generated for the agentic-challenges investigation.
"""
from __future__ import annotations
import json
from process_bigraph.visualization import as_visualization


@as_visualization(
    inputs={
        'temperature': 'list[float]',
        'biomass': 'list[float]',
        'viability': 'list[float]',
        't_tol': 'float',
    },
    name='BoundedCellGrowth',
    demo={
        # Rising temperature ramp (°C) crossing the t_tol=43 °C tolerance.
        'temperature': [30, 32, 34, 36, 38, 40, 42, 43, 44, 46, 48, 50],
        # Monod-SATURATING growth: rises then plateaus (bounded), a.u.
        'biomass': [0.20, 0.55, 0.95, 1.40, 1.85, 2.20, 2.45, 2.55, 2.55, 2.55, 2.55, 2.55],
        # Viability holds ~1.0 below tolerance, then cliffs to ~0 past t_tol.
        'viability': [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.15, 0.02, 0.0, 0.0],
        't_tol': 43.0,
    },
)
def update_bounded_cell_growth(state):
    """Biomass (Monod-saturating, left axis) and viability (right axis) vs a
    rising temperature ramp, with the t_tol thermal-death threshold marked."""
    temp = state['temperature']
    biomass = state['biomass']
    viability = state['viability']
    t_tol = state['t_tol']

    traces = [
        {
            'x': temp, 'y': biomass, 'type': 'scatter', 'mode': 'lines+markers',
            'name': 'biomass (Monod-saturating)',
            'line': {'color': '#10b981', 'width': 3},
            'marker': {'size': 6},
            'yaxis': 'y',
            'hovertemplate': 'T = %{x} °C<br>biomass = %{y:.2f} a.u.<extra></extra>',
        },
        {
            'x': temp, 'y': viability, 'type': 'scatter', 'mode': 'lines+markers',
            'name': 'viability (thermal cliff)',
            'line': {'color': '#6366f1', 'width': 3},
            'marker': {'size': 6},
            'yaxis': 'y2',
            'hovertemplate': 'T = %{x} °C<br>viability = %{y:.2f}<extra></extra>',
        },
    ]
    layout = {
        'title': {'text': 'Bounded growth to a cliff: biomass saturates while viability collapses at t_tol = 43 °C'},
        'shapes': [{
            'type': 'line', 'xref': 'x', 'yref': 'paper',
            'x0': t_tol, 'x1': t_tol, 'y0': 0, 'y1': 1,
            'line': {'dash': 'dash', 'color': '#f43f5e', 'width': 2},
        }],
        'annotations': [{
            'xref': 'x', 'yref': 'paper', 'x': t_tol, 'y': 1.02,
            'text': f'ThermalDeath tolerance t_tol = {t_tol:.0f} °C',
            'showarrow': False, 'font': {'size': 11, 'color': '#f43f5e'},
            'xanchor': 'center', 'yanchor': 'bottom',
        }],
        'legend': {'orientation': 'h', 'x': 0.5, 'y': -0.2, 'xanchor': 'center'},
        'margin': {'l': 60, 'r': 60, 't': 60, 'b': 60},
        'xaxis': {'title': {'text': 'temperature (°C)'}},
        'yaxis': {'title': {'text': 'biomass (a.u.)'}, 'range': [0, max(biomass) * 1.2], 'color': '#10b981'},
        'yaxis2': {
            'title': {'text': 'viability (fraction)'}, 'range': [0, 1.08],
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
