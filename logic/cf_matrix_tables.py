from dash import html
import pandas as pd
from typing import Dict, List, Optional


def build_cf_matrix_row_pct_n_table(
    df_demo: pd.DataFrame,
    *,
    cf_col: str,
    category_order: List,
    category_labels: Dict,
    age_col: str = "Age_Bin",
    gender_col: str = "Gender_Label",
    eth_col: str = "Ethnicity_Label",
    age_levels: Optional[List[str]] = None,
    gender_levels: Optional[List[str]] = None,
    eth_levels: Optional[List[str]] = None,
    title: str = "Complicating Factor (Row-wise %, n)",
    pct_decimals: int = 1,
    total_denominator: Optional[int] = None,  # ✅ NEW: if None, auto-compute
):
    """
    - Subgroup cells (Age/Gender/Ethnicity): ROW-wise %
        pct = subgroup_n / (total in that CF category) * 100

    - Total column: % of OVERALL sample (e.g., /2499)
        pct_total = (total in that CF category) / total_denominator * 100
    """

    if age_levels is None:
        age_levels = ["<40", "40–65", "65–85", ">=85"]
    if gender_levels is None:
        gender_levels = ["Male", "Female"]
    if eth_levels is None:
        eth_levels = ["Chinese", "Malay", "Indian", "Others"]

    # ✅ Overall denominator for the Total column
    if total_denominator is None:
        # only rows that belong to these CF categories
        total_denominator = int(df_demo[cf_col].isin(category_order).sum())

    # Styles
    th_style = {
        "border": "1px solid #000",
        "padding": "8px",
        "textAlign": "center",
        "verticalAlign": "middle",
        "fontWeight": "bold",
        "backgroundColor": "#f5f5f5",
        "whiteSpace": "normal",
    }
    th_left = {**th_style, "textAlign": "left"}

    td_left = {
        "border": "1px solid #000",
        "padding": "8px",
        "textAlign": "left",
        "verticalAlign": "middle",
        "fontWeight": 500,
        "whiteSpace": "normal",
    }
    td_center = {
        "border": "1px solid #000",
        "padding": "12px 10px",
        "textAlign": "center",
        "verticalAlign": "middle",
        "lineHeight": "1.3",
    }

    def td_pct_n(n: int, denom: int):
        if denom <= 0:
            return html.Td("—", style=td_center)
        pct = (n / denom) * 100
        return html.Td(
            [
                html.Div(
                    f"{pct:.{pct_decimals}f}%",
                    style={"fontWeight": "600", "fontSize": "14px", "marginBottom": "6px"},
                ),
                html.Div(f"(n={n})", style={"fontSize": "11px", "color": "#666"}),
            ],
            style=td_center,
        )

    # Header
    thead = html.Thead(
        [
            html.Tr(
                [
                    html.Th("Category", style=th_left),
                    html.Th("Total (N=2499)", style=th_style),
                    html.Th("Age Group (years)", colSpan=len(age_levels), style=th_style),
                    html.Th("Gender", colSpan=len(gender_levels), style=th_style),
                    html.Th("Ethnicity", colSpan=len(eth_levels), style=th_style),
                ]
            ),
            html.Tr(
                [
                    html.Th("", style=th_left),
                    html.Th("", style=th_style),
                    *[html.Th(a, style=th_style) for a in age_levels],
                    *[html.Th(g, style=th_style) for g in gender_levels],
                    *[html.Th(e, style=th_style) for e in eth_levels],
                ]
            ),
        ]
    )

    body_rows = []

    for cat in category_order:
        cat_mask = df_demo[cf_col].eq(cat)
        denom_row = int(cat_mask.sum())  # ✅ CF category total (row denominator)

        row_cells = [html.Td(category_labels.get(cat, str(cat)), style=td_left)]

        # ✅ Total column: % of overall denominator (e.g., /2499)
        if denom_row > 0 and total_denominator > 0:
            pct_total = (denom_row / total_denominator) * 100
            row_cells.append(
                html.Td(
                    [
                        html.Div(
                            f"{pct_total:.{pct_decimals}f}%",
                            style={"fontWeight": "600", "fontSize": "14px", "marginBottom": "6px"},
                        ),
                        html.Div(f"(n={denom_row})", style={"fontSize": "11px", "color": "#666"}),
                    ],
                    style=td_center,
                )
            )
        else:
            row_cells.append(html.Td("—", style=td_center))

        # Age columns: row-wise %
        for a in age_levels:
            n = int((cat_mask & (df_demo[age_col] == a)).sum())
            row_cells.append(td_pct_n(n, denom_row))

        # Gender columns: row-wise %
        for g in gender_levels:
            n = int((cat_mask & (df_demo[gender_col] == g)).sum())
            row_cells.append(td_pct_n(n, denom_row))

        # Ethnicity columns: row-wise %
        for e in eth_levels:
            n = int((cat_mask & (df_demo[eth_col] == e)).sum())
            row_cells.append(td_pct_n(n, denom_row))

        body_rows.append(html.Tr(row_cells))

    table = html.Table(
        [thead, html.Tbody(body_rows)],
        style={
            "width": "100%",
            "borderCollapse": "collapse",
            "fontFamily": "monospace",
            "fontSize": "14px",
        },
    )

    return html.Div(
        [
            html.H3(title),
            html.Div(
                table,
                style={
                    "border": "1px solid #d0d0d0",
                    "borderRadius": "10px",
                    "overflowX": "auto",
                    "background": "white",
                    "padding": "12px",
                },
            ),
        ]
    )

# Backward-compatible alias
build_cf_matrix_pct_n_table = build_cf_matrix_row_pct_n_table
