import pandas as pd
from dash import html, dcc
import dash_bootstrap_components as dbc

from logic.just_global_impressions import (
    gi_unique_distribution_chart,
    gi_stepwise_escalation_chart,
    gi_utilisation_section,
    gi_demographics_by_gi_section,
)

# ----------------------------
# Small reusable card helper
# ----------------------------
def section_card(title: str, body, subtitle: str | None = None, class_name="mb-3"):
    return dbc.Card(
        dbc.CardBody(
            [
                html.H4(title, style={"marginBottom": "6px"}),
                html.Div(
                    subtitle,
                    style={"fontSize": "13px", "opacity": 0.75, "marginBottom": "12px"},
                ) if subtitle else None,
                body,
            ]
        ),
        style={
            "borderRadius": "14px",
            "boxShadow": "0 2px 10px rgba(0,0,0,0.06)",
            "border": "1px solid rgba(0,0,0,0.05)",
        },
        className=class_name,
    )


def GI_unique_summary_layout(df: pd.DataFrame):
    fig = gi_unique_distribution_chart(df)
    demo_tables = gi_demographics_by_gi_section(df)
    util_section = gi_utilisation_section(df)

    return dbc.Container(
        [
            html.H3("Global Impressions Overview", className="mb-3"),

            section_card(
                title="Unique GI Distribution",
                body=dcc.Graph(figure=fig, config={"displayModeBar": False}),
            ),

            section_card(
                title="Demographics × GI",
                body=demo_tables,
            ),

            section_card(
                title="GI × Healthcare Utilisation",
                body=util_section,
            ),
        ],
        fluid=True,
        style={"paddingTop": "10px", "paddingBottom": "10px"},
    )


def GI_stepwise_summary_layout(df: pd.DataFrame):
    fig = gi_stepwise_escalation_chart(df)

    return dbc.Container(
        [
            html.H3("Global Impression — Stepwise Escalation Summary", className="mb-3"),

            section_card(
                title="Stepwise Escalation (Mild → Severe)",
                subtitle="Overlaps promoted at each step",
                body=dcc.Graph(figure=fig, config={"displayModeBar": False}),
            ),
        ],
        fluid=True,
        style={"paddingTop": "10px", "paddingBottom": "10px"},
    )
