from dash import html, dash_table
import pandas as pd
import dash_bootstrap_components as dbc

# =============================== BINARY QUESTION GROUP TABLE ===============================
def binary_question_group_table(
    df,
    cols,
    row_labels,
    code_0 = 1,
    code_1 = 2,
    code_2 = 3,
    code_3_4 = 4,
    code_5_8 = 5,
    code_9_plus = 6,
    code_refused=777,
    code_not_applicable=999,
    title_text=None,
):
    rows = []
    total_0 = 0
    total_1 = 0
    total_2 = 0
    total_3_4 = 0
    total_5_8 = 0
    total_9_plus = 0
    total_refused = 0
    total_na = 0

    for col, label in zip(cols, row_labels):

        count_0 = (df[col] == code_0).sum()
        count_1 = (df[col] == code_1).sum()
        count_2 = (df[col] == code_2).sum()
        count_3_4 = (df[col] == code_3_4).sum()
        count_5_8 = (df[col] == code_5_8).sum()
        count_9_plus = (df[col] == code_9_plus).sum()
        refused_count = (df[col] == code_refused).sum()
        na_count = (df[col] == code_not_applicable).sum()

        # Total responses now include *all* types
        total = count_0 + count_1 + count_2 + count_3_4 + count_5_8 + count_9_plus + refused_count + na_count

        total_0 += count_0
        total_1 += count_1
        total_2 += count_2
        total_3_4 += count_3_4
        total_5_8 += count_5_8
        total_9_plus += count_9_plus
        total_refused += refused_count
        total_na += na_count

        rows.append({
            "Question": label,
            "0": int(count_0),
            "1": int(count_1),
            "2": int(count_2),
            "3-4": int(count_3_4),
            "5-8": int(count_5_8),
            "9+": int(count_9_plus),
            "Refused (777)": int(refused_count),
            "Not Applicable (999)": int(na_count),
            "Total": int(total),
        })

    # Add total row
    rows.append({
        "Question": "Total",
        "0": int(total_0),
        "1": int(total_1),
        "2": int(total_2),
        "3-4": int(total_3_4),
        "5-8": int(total_5_8),
        "9+": int(total_9_plus),
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
