from dash import html, dash_table
import pandas as pd
import dash_bootstrap_components as dbc

# =============================== BINARY QUESTION GROUP TABLE ===============================
def binary_question_group_table(
    df,
    cols,
    row_labels,
    code_stronglyDisagree=0,
    code_Disagree=1,
    code_Neither=2,
    code_Agree=3,
    code_StronglyAgree=4,
    code_refused=777,
    code_not_applicable=999,
    title_text=None,
):
    rows = []
    total_stronglyDisagree = 0
    total_Disagree = 0
    total_Neither = 0
    total_Agree = 0
    total_StronglyAgree = 0
    total_refused = 0
    total_na = 0

    for col, label in zip(cols, row_labels):

        stronglyDisagree_count = (df[col] == code_stronglyDisagree).sum()
        disagree_count = (df[col] == code_Disagree).sum()
        neither_count = (df[col] == code_Neither).sum()
        agree_count = (df[col] == code_Agree).sum()
        stronglyAgree_count = (df[col] == code_StronglyAgree).sum()
        refused_count = (df[col] == code_refused).sum()
        na_count = (df[col] == code_not_applicable).sum()

        # Total responses now include *all* types
        total = stronglyDisagree_count + disagree_count + neither_count + agree_count + stronglyAgree_count + refused_count + na_count

        total_stronglyDisagree += stronglyDisagree_count
        total_Disagree += disagree_count
        total_Neither += neither_count
        total_Agree += agree_count
        total_StronglyAgree += stronglyAgree_count
        total_refused += refused_count
        total_na += na_count

        rows.append({
            "Question": label,
            "Strongly Disagree (0)": int(stronglyDisagree_count),
            "Disagree (1)": int(disagree_count),
            "Neither (2)": int(neither_count),
            "Agree (3)": int(agree_count),
            "Strongly Agree (4)": int(stronglyAgree_count),
            "Refused (777)": int(refused_count),
            "Not Applicable (999)": int(na_count),
            "Total": int(total),
        })

    # Add total row
    rows.append({
        "Question": "Total",
        "Strongly Disagree (0)": int(total_stronglyDisagree),
        "Disagree (1)": int(total_Disagree),
        "Neither (2)": int(total_Neither),
        "Agree (3)": int(total_Agree),
        "Strongly Agree (4)": int(total_StronglyAgree),
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
