"""SpatialCompetitionSourcingAudit — sourcing-audit report card for the spatial-competition study.

The study asks how to source a model for the required capabilities spatial,
dfba and diffusion. The audit's verdict is REUSE spatio-flux (which performs
spatial dynamic flux-balance competition for a shared diffusing nutrient), and
the gate PASSES: all four audit axes — source_fit, reinvention,
novelty_justified, survey_recorded — grade within_tol. A non-spatial module
would trip source_fit. This figure lays the four axes out as a report card:
every green bar is an axis within tolerance; a red bar would fail the gate.

Generated for the model-sourcing investigation. Demo data are the study's real
audit-axis grades and the real run summary (ran t=5.0; glucose 10.0->8.31,
acetate 0.0->0.083).
"""
from __future__ import annotations
import json
from process_bigraph.visualization import as_visualization


@as_visualization(
    inputs={'axes': 'list[string]', 'status': 'list[string]'},
    name='SpatialCompetitionSourcingAudit',
    demo={'axes': ['source_fit', 'reinvention', 'novelty_justified', 'survey_recorded'],
          'status': ['within_tol', 'within_tol', 'within_tol', 'within_tol']},
)
def update_spatial_competition_sourcing_audit(state):
    """Horizontal report card of the four sourcing-audit axes, green=within_tol
    and red=mismatch, titled with the reuse-spatio-flux decision and the PASS gate."""
    axes = state['axes']
    status = state['status']
    order = list(reversed(list(zip(axes, status))))  # first axis on top
    y = [a for a, _ in order]
    vals = [1.0 for _ in order]
    colors = ['#10b981' if s == 'within_tol' else '#f43f5e' for _, s in order]
    labels = [s for _, s in order]
    gate_pass = all(s == 'within_tol' for s in status)
    traces = [{
        'x': vals, 'y': y, 'type': 'bar', 'orientation': 'h',
        'marker': {'color': colors},
        'text': labels, 'textposition': 'inside', 'insidetextanchor': 'middle',
        'textfont': {'color': 'white', 'size': 12},
        'hovertemplate': '%{y}: %{text}<extra></extra>',
        'name': 'audit axis',
    }]
    layout = {
        'title': {'text': 'Sourcing decision: REUSE spatio-flux — gate '
                          + ('PASS' if gate_pass else 'FAIL')
                          + ' (spatial · dfba · diffusion)'},
        'annotations': [{
            'xref': 'paper', 'yref': 'paper', 'x': 0.5, 'y': 1.0,
            'text': 'green = within_tol · red = mismatch    |    real run: t=5.0; glucose 10.0→8.31, acetate 0.0→0.083',
            'showarrow': False, 'font': {'size': 11, 'color': '#475569'},
            'xanchor': 'center', 'yanchor': 'bottom',
        }],
        'margin': {'l': 130, 'r': 20, 't': 70, 'b': 40},
        'xaxis': {'range': [0, 1.05], 'showticklabels': False, 'showgrid': False, 'zeroline': False},
        'yaxis': {'title': {'text': 'audit axis'}, 'automargin': True},
        'showlegend': False,
    }
    return {'html': (
        '<div id="viz" style="height:360px"></div>'
        '<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>'
        '<script>Plotly.newPlot("viz",'
        + json.dumps(traces) + ',' + json.dumps(layout)
        + ', {responsive:true, displayModeBar:false});</script>'
    )}
