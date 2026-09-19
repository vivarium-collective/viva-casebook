"""SourcingAuditNovel — the sourcing audit report-card for a justified build-new.

novel-mechanism is a MODEL-SOURCING study for required capabilities
[quantum_signal, exotic_transport], which no catalogued module implements. The audit
graded the decision build-new as a PASS: all four sourcing axes — source_fit,
reinvention, novelty_justified, survey_recorded — land within_tol. This report-card
shows each axis green (within_tol), making the point that building a new module here is
the correct call, not reinvention: there is simply nothing in the catalog to reuse.

Generated for the study's declared visualization. Demo data are the study's real audit
axis values (all within_tol; gate pass; decision build-new).
"""
from __future__ import annotations
import json
from process_bigraph.visualization import as_visualization


@as_visualization(
    inputs={'axes': 'list[string]', 'values': 'list[string]'},
    name='SourcingAuditNovel',
    demo={'axes': ['source_fit', 'reinvention', 'novelty_justified', 'survey_recorded'],
          'values': ['within_tol', 'within_tol', 'within_tol', 'within_tol']},
)
def update_sourcing_audit_novel(state):
    """Horizontal report-card of the four sourcing-audit axes, green within_tol /
    red mismatch — decision build-new, gate PASS."""
    axes = state['axes']
    values = state['values']
    colors = ['#10b981' if v == 'within_tol' else '#f43f5e' for v in values]
    heights = [1.0 for _ in values]
    traces = [{
        'x': heights, 'y': axes, 'type': 'bar', 'orientation': 'h',
        'marker': {'color': colors},
        'text': values, 'textposition': 'inside', 'insidetextanchor': 'middle',
        'textfont': {'color': '#ffffff'},
        'hovertemplate': '%{y}: %{text}<extra></extra>',
        'customdata': values,
    }]
    layout = {
        'title': {'text': 'Sourcing audit — decision: build-new · gate: PASS (novelty justified)'},
        'annotations': [{
            'xref': 'paper', 'yref': 'paper', 'x': 0.5, 'y': 1.0,
            'text': 'no catalogued module covers [quantum_signal, exotic_transport] — green = within_tol',
            'showarrow': False, 'font': {'size': 11, 'color': '#475569'},
            'xanchor': 'center', 'yanchor': 'bottom',
        }],
        'margin': {'l': 130, 'r': 20, 't': 60, 'b': 30},
        'xaxis': {'range': [0, 1], 'showticklabels': False, 'zeroline': False},
        'yaxis': {'title': {'text': 'audit axis'}, 'autorange': 'reversed'},
    }
    return {'html': (
        '<div id="viz" style="height:360px"></div>'
        '<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>'
        '<script>Plotly.newPlot("viz",'
        + json.dumps(traces) + ',' + json.dumps(layout)
        + ', {responsive:true, displayModeBar:false});</script>'
    )}
