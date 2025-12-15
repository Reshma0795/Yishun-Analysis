# logic/mapping_helpers.py

import pandas as pd
from dash import html
from dash import dash_table


def build_mapping_table(rows, title=None):
    """
    rows: list of dicts, e.g.
    [
      {
        "Complicating Factor": "",
        "Mapped Question No from Survey": "",
        "Question Description": "...",
        "Levels": "...",
        "Data Mapping": "...",
        "Coding": "",
      }
    ]
    """
    df = pd.DataFrame(rows)

    table = dash_table.DataTable(
        data=df.to_dict("records"),
        columns=[{"name": c, "id": c} for c in df.columns],
        style_cell={
            "whiteSpace": "pre-line",
            "height": "auto",
            "textAlign": "left",
            "fontSize": 12,
            "padding": "6px",
        },
        style_header={
            "fontWeight": "bold",
            "backgroundColor": "#f5f5f5",
        },
        style_table={
            "overflowX": "auto",
        },
    )

    children = [table]
    if title:
        children.insert(0, html.H4(title, style={"marginBottom": "6px"}))

    return html.Div(children, style={"marginBottom": "20px"})
