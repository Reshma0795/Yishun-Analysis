from dash import html, dash_table
import pandas as pd

def disruptive_value_counts_table(
    df,
    cols,
    row_labels=None,
    code_pass=1,
    code_fail=2,
    code_refused=777,
    code_not_applicable=999,
    title_text=None,
):
    rows = []
    total_pass = total_fail = total_refused = total_na = 0

    if row_labels is None:
        row_labels = cols

    for col, label in zip(cols, row_labels):
        pass_count = (df[col] == code_pass).sum()
        fail_count = (df[col] == code_fail).sum()
        refused_count = (df[col] == code_refused).sum()
        na_count = (df[col] == code_not_applicable).sum()

        total = int(pass_count + fail_count + refused_count + na_count)

        total_pass += pass_count
        total_fail += fail_count
        total_refused += refused_count
        total_na += na_count

        rows.append(
            {
                "Question": label,
                "Pass (1)": int(pass_count),
                "Fail (2)": int(fail_count),
                "X / Refused (777)": int(refused_count),
                "Not Applicable (999)": int(na_count),
                "Total": total,
            }
        )

    rows.append(
        {
            "Question": "Total",
            "Pass (1)": int(total_pass),
            "Fail (2)": int(total_fail),
            "X / Refused (777)": int(total_refused),
            "Not Applicable (999)": int(total_na),
            "Total": int(total_pass + total_fail + total_refused + total_na),
        }
    )

    table_df = pd.DataFrame(rows)

    table = dash_table.DataTable(
        data=table_df.to_dict("records"),
        columns=[{"name": c, "id": c} for c in table_df.columns],
        style_cell={"textAlign": "left", "padding": "4px", "fontFamily": "monospace"},
        style_header={"fontWeight": "bold", "backgroundColor": "#5b3fd3", "color": "white"},
        style_data_conditional=[
            {"if": {"row_index": len(rows) - 1}, "fontWeight": "bold", "backgroundColor": "#f5f5f5"}
        ],
    )

    children = []
    if title_text:
        children.append(html.H5(title_text, style={"fontSize": "14px", "fontWeight": "600", "marginBottom": "8px"}))
    children.append(table)

    return html.Div(children)
