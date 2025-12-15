from dash import html
import dash_bootstrap_components as dbc

GI_COLUMNS = [
    "GI no",
    "SST Version 3",
    "SST V3 definition",
    "SST V3 example",
    "Eligibility for inclusion (SIGNS I and II)",
]

def gi_one_row_table(gi_row: dict, table_title: str = "Table A1: Global Impression Segments"):
    """
    gi_row keys expected:
      - gi_no
      - sst_v3
      - definition
      - example
      - eligibility
    """

    def cell(text, width=None, bold=False):
        return html.Td(
            html.Div(
                text,
                style={
                    "whiteSpace": "pre-line",   # respects \n
                    "lineHeight": "1.35",
                    "fontWeight": "700" if bold else "400",
                },
            ),
            style={"verticalAlign": "top", **({"width": width} if width else {})},
        )

    header = html.Thead(
        html.Tr([html.Th(c, style={"textAlign": "left", "verticalAlign": "top"}) for c in GI_COLUMNS])
    )

    body = html.Tbody(
        [
            html.Tr(
                [
                    cell(gi_row.get("gi_no", ""), width="6%", bold=True),
                    cell(gi_row.get("sst_v3", ""), width="14%", bold=True),
                    cell(gi_row.get("definition", ""), width="32%"),
                    cell(gi_row.get("example", ""), width="14%"),
                    cell(gi_row.get("eligibility", ""), width="34%"),
                ]
            )
        ]
    )

    table = dbc.Table(
        [header, body],
        bordered=True,
        hover=False,
        responsive=True,
        style={
            "backgroundColor": "white",
            "marginBottom": "0px",
        },
    )

    return html.Div(
        [
            html.H5(table_title, style={"fontWeight": "700"}),
            table,
        ]
    )
