import pandas as pd
from dash import html, dcc

from logic.just_global_impressions import gi_unique_distribution_chart, gi_stepwise_escalation_chart

def GI_unique_summary_layout(df: pd.DataFrame):
    fig = gi_unique_distribution_chart(df)
    return html.Div([
        html.H3("Global Impression — Unique Assignment Summary"),
        dcc.Graph(figure=fig, config={"displayModeBar": False}),
    ])

def GI_stepwise_summary_layout(df: pd.DataFrame):
    fig = gi_stepwise_escalation_chart(df)
    return html.Div([
        html.H3("Global Impression — Stepwise Escalation Summary"),
        dcc.Graph(figure=fig, config={"displayModeBar": False}),
    ])   