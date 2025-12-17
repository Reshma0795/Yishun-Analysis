from dash import html, dash_table
import dash_bootstrap_components as dbc
import pandas as pd
from dash import html

def nursing_question_group_table(
    df,
    cols,
    row_labels,
    code_not_mentioned=0,
    code_mentioned=1,
    code_not_applicable=999,
    title_text=None,
):
    """
    Build a table like the Q155/Q167 one, but for Nursing (Q107_1–Q107_4),
    showing counts of:
      - 0 = Not mentioned
      - 1 = Mentioned
      - 999 = Not applicable
    """

    rows = []
    total_not = 0
    total_yes = 0
    total_na = 0

    for col, label in zip(cols, row_labels):
        not_count = (df[col] == code_not_mentioned).sum()
        yes_count = (df[col] == code_mentioned).sum()
        na_count = (df[col] == code_not_applicable).sum()

        total_not += not_count
        total_yes += yes_count
        total_na += na_count

        rows.append(
            {
                "Question": label,
                "Not mentioned (0)": int(not_count),
                "Mentioned (1)": int(yes_count),
                "Not applicable (999)": int(na_count),
                "Total": int(not_count + yes_count + na_count),
            }
        )

    # Total row (sum across all items)
    rows.append(
        {
            "Question": "Total",
            "Not mentioned (0)": int(total_not),
            "Mentioned (1)": int(total_yes),
            "Not applicable (999)": int(total_na),
            "Total": int(total_not + total_yes + total_na),
        }
    )

    table_df = pd.DataFrame(rows)

    table = dash_table.DataTable(
        data=table_df.to_dict("records"),
        columns=[{"name": c, "id": c} for c in table_df.columns],
        style_cell={
            "textAlign": "left",
            "padding": "4px",
            "fontFamily": "monospace",
        },
        style_header={
            "fontWeight": "bold",
            "backgroundColor": "#5b3fd3",
            "color": "white",
        },
        style_data_conditional=[
            {
                "if": {"row_index": len(rows) - 1},
                "fontWeight": "bold",
                "backgroundColor": "#f5f5f5",
            }
        ],
    )

    children = []
    if title_text:
        children.append(
            html.H5(
                title_text,
                style={
                    "fontSize": "14px",
                    "fontWeight": "600",
                    "marginBottom": "8px",
                },
            )
        )

    children.append(table)
    return html.Div(children)


def nursing_response_cards(
    df,
    cols,
    code_not_mentioned=0,
    code_mentioned=1,
    code_not_applicable=999,
    title_prefix="Q107 – Nursing type skilled task needs",
):
    """
    Build 3 cards showing % of:
      - 0 = Not mentioned
      - 1 = Mentioned
      - 999 = Not applicable
    across all responses in the given columns.
    """

    # Flatten all values across the selected columns
    values = df[cols].values.ravel()

    # Keep only relevant codes
    valid_mask = (values == code_not_mentioned) | (values == code_mentioned) | (
        values == code_not_applicable
    )
    valid_values = values[valid_mask]

    total = len(valid_values) if len(valid_values) > 0 else 1  # avoid divide-by-zero

    count_not = (valid_values == code_not_mentioned).sum()
    count_yes = (valid_values == code_mentioned).sum()
    count_na = (valid_values == code_not_applicable).sum()

    pct_not = (count_not / total) * 100
    pct_yes = (count_yes / total) * 100
    pct_na = (count_na / total) * 100

    def _card(title, subtitle, pct, n, color):
        return dbc.Card(
            [
                dbc.CardBody(
                    [
                        html.Div(
                            title,
                            style={
                                "fontSize": "12px",
                                "fontWeight": "600",
                                "marginBottom": "4px",
                            },
                        ),
                        html.Div(
                            subtitle,
                            style={
                                "fontSize": "11px",
                                "fontWeight": "500",
                                "marginBottom": "8px",
                            },
                        ),
                        html.Div(
                            f"{pct:.1f}%",
                            style={
                                "fontSize": "24px",
                                "fontWeight": "700",
                                "marginBottom": "4px",
                            },
                        ),
                        html.Div(
                            f"n = {n}",
                            style={"fontSize": "11px", "color": "#555"},
                        ),
                    ]
                )
            ],
            style={
                "borderRadius": "10px",
                "boxShadow": "0 2px 6px rgba(0,0,0,0.08)",
                "borderLeft": f"4px solid {color}",
                "height": "130px",
            },
        )

    return dbc.Row(
        [
            dbc.Col(
                _card(
                    title=f"{title_prefix} responses",
                    subtitle="Not mentioned (0)",
                    pct=pct_not,
                    n=int(count_not),
                    color="#999999",
                ),
                md=4,
            ),
            dbc.Col(
                _card(
                    title=f"{title_prefix} responses",
                    subtitle="Mentioned (1)",
                    pct=pct_yes,
                    n=int(count_yes),
                    color="#28a745",  # green-ish
                ),
                md=4,
            ),
            dbc.Col(
                _card(
                    title=f"{title_prefix} responses",
                    subtitle="Not applicable (999)",
                    pct=pct_na,
                    n=int(count_na),
                    color="#6c757d",  # grey
                ),
                md=4,
            ),
        ],
        className="mb-4",
    )

