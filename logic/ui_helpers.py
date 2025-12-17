import dash_bootstrap_components as dbc
from dash import html, dcc

def chart_card(
    figure,
    title=None,
    subtitle=None,
    height="420px",
):
    return dbc.Card(
        dbc.CardBody(
            [
                # Optional title
                title and html.H5(
                    title,
                    style={
                        "fontWeight": "600",
                        "marginBottom": "4px",
                    },
                ),

                # Optional subtitle
                subtitle and html.Div(
                    subtitle,
                    style={
                        "fontSize": "12px",
                        "color": "#6c757d",
                        "marginBottom": "10px",
                    },
                ),

                # Chart
                dcc.Graph(
                    figure=figure,
                    config={"displayModeBar": False},
                    style={"height": height},
                ),
            ]
        ),
        style={
            "borderRadius": "16px",
            "boxShadow": "0 6px 18px rgba(0,0,0,0.08)",
            "border": "1px solid rgba(0,0,0,0.06)",
            "backgroundColor": "white",
        },
    )
