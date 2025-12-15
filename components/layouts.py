from dash import html, dcc
from dash.dash_table import DataTable

def section_header(text):
    return html.H4(text, style={"marginTop": "20px"})

def table_component(df):
    return DataTable(
        data=df.to_dict("records"),
        columns=[{"name": c, "id": c} for c in df.columns],
        style_cell={"textAlign": "center"},
        style_header={"fontWeight": "bold"}
    )
