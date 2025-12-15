from dash import html, dash_table
import pandas as pd
import dash_bootstrap_components as dbc

# =============================== BINARY QUESTION GROUP TABLE ===============================
def binary_question_group_table(
    df,
    cols,
    row_labels,
    code_yes=1,
    code_no=2,
    code_refused=777,
    code_not_applicable=999,
    title_text=None,
):
    rows = []
    total_yes = 0
    total_no = 0
    total_refused = 0
    total_na = 0

    for col, label in zip(cols, row_labels):

        yes_count = (df[col] == code_yes).sum()
        no_count = (df[col] == code_no).sum()
        refused_count = (df[col] == code_refused).sum()
        na_count = (df[col] == code_not_applicable).sum()

        # Total responses now include *all* types
        total = yes_count + no_count + refused_count + na_count

        total_yes += yes_count
        total_no += no_count
        total_refused += refused_count
        total_na += na_count

        rows.append({
            "Question": label,
            "Yes (1)": int(yes_count),
            "No (2)": int(no_count),
            "Refused (777)": int(refused_count),
            "Not Applicable (999)": int(na_count),
            "Total": int(total),
        })

    # Add total row
    rows.append({
        "Question": "Total",
        "Yes (1)": int(total_yes),
        "No (2)": "",
        "Refused (777)": int(total_refused),
        "Not Applicable (999)": int(total_na),
        "Total": "",
    })

    table_df = pd.DataFrame(rows)

    table = dash_table.DataTable(
        data=table_df.to_dict("records"),
        columns=[{"name": c, "id": c} for c in table_df.columns],
        style_cell={"textAlign": "left", "padding": "4px", "fontFamily": "monospace"},
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
                style={"fontSize": "14px", "fontWeight": "600", "marginBottom": "8px"},
            )
        )

    children.append(table)

    return html.Div(children)

# =============================== SUMMARY CARDS ===============================

def response_summary_cards(
    df,
    cols,
    title="Response distribution",
    code_yes=1,
    code_no=2,
    code_refused=777,
    code_not_applicable=999,
):
    """
    Creates 4 cards showing % Yes / No / Refused / Not applicable
    for a group of columns.
    """

    # Count across ALL columns in the group
    yes_count = (df[cols] == code_yes).sum().sum()
    no_count = (df[cols] == code_no).sum().sum()
    refused_count = (df[cols] == code_refused).sum().sum()
    na_count = (df[cols] == code_not_applicable).sum().sum()

    total = yes_count + no_count + refused_count + na_count
    if total == 0:
        total = 1  # avoid division by zero

    def pct(x):
        return 100.0 * x / total

    cards_data = [
        ("Yes (1)", yes_count, pct(yes_count), "#4caf50"),
        ("No (2)", no_count, pct(no_count), "#2196f3"),
        ("Refused (777)", refused_count, pct(refused_count), "#ff9800"),
        ("Not applicable (999)", na_count, pct(na_count), "#9e9e9e"),
    ]

    card_components = []
    for label, count, percent, color in cards_data:
        card_components.append(
            dbc.Col(
                dbc.Card(
                    dbc.CardBody(
                        [
                            html.Div(title, className="text-muted", style={"fontSize": "11px"}),
                            html.Div(label, style={"fontSize": "13px", "fontWeight": "600"}),
                            html.H4(f"{percent:.1f}%", className="mt-1 mb-1"),
                            html.Small(f"n = {int(count)}", className="text-muted"),
                        ]
                    ),
                    style={
                        "borderRadius": "12px",
                        "boxShadow": "0 4px 10px rgba(0, 0, 0, 0.08)",
                        "backgroundColor": "white",
                        "borderLeft": f"6px solid {color}",
                    },
                ),
                md=3,
                sm=6,
                xs=12,
            )
        )

    return html.Div(
        [
            dbc.Row(card_components, className="g-3 mb-3"),
        ]
    )