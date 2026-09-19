"""SourcingAuditTrap — the sourcing audit catching the wrong-reuse trap before lock.

trap-wrong-reuse is the DELIBERATE TRAP study. The task requires [physics_2d, spatial].
viva-munk is tempting because it looks like physics, but it provides only 2D rigid-body
physics and lacks the required `spatial` capability. The audit correctly caught this: the
source_fit axis grades MISMATCH and the gate FAILS, while the other three axes
(reinvention, novelty_justified, survey_recorded) stay within_tol — so the failure is
isolated to source_fit, not over-building. This report-card colors source_fit red as the
caught mismatch and frames the FAIL as the audit working as intended: the wrong module is
rejected before the behavior tests are locked.

Generated for the study's declared visualization. Demo data are the study's real audit
axis values (source_fit mismatch, others within_tol; gate fail; decision reuse viva-munk).
"""
from __future__ import annotations
import json
from process_bigraph.visualization import as_visualization


@as_visualization(
    inputs={'axes': 'list[string]', 'values': 'list[string]'},
    name='SourcingAuditTrap',
    demo={'axes': ['source_fit', 'reinvention', 'novelty_justified', 'survey_recorded'],
          'values': ['mismatch', 'within_tol', 'within_tol', 'within_tol']},
)
def update_sourcing_audit_trap(state):
    """Horizontal report-card of the four sourcing-audit axes, source_fit flagged red as
    the caught mismatch — audit correctly rejects reuse viva-munk before tests lock."""
    axes = state['axes']
    values = state['values']
    colors = ['#f43f5e' if v == 'mismatch' else '#10b981' for v in values]
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
        'title': {'text': 'Sourcing audit caught the trap — reuse viva-munk rejected before tests lock (gate: FAIL)'},
        'annotations': [{
            'xref': 'paper', 'yref': 'paper', 'x': 0.5, 'y': 1.0,
            'text': 'viva-munk lacks the required `spatial` capability — red source_fit = mismatch (audit working as intended)',
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
