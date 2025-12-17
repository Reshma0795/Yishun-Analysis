from dash import html
import pandas as pd
from typing import Dict, List, Optional

from logic.utilization_helpers import build_gp_visits  # you already use this


def build_cf_x_utilization_crosstab_table(
    df_demo: pd.DataFrame,
    *,
    cf_col: str,
    category_order: List,
    category_labels: Dict,
    util_qcodes: List[str],
    util_question_meta: Dict,   # HEALTHCARE_UTILIZATION_QUESTIONS
    title: str = "Cross-tab: CF × Healthcare Utilization",
    mode: str = "valid",        # "valid" (non-null) OR "ge1" (>=1) OR "sum"
):
    """
    Builds an Excel-style table:

      Rows: CF categories (using category_order/category_labels)
      Cols: Q78/Q85/Q91/Q93/Q96/Q103 (or any util_qcodes)

    Cell meanings (choose via mode):
      - mode="valid": count of respondents with a VALID utilization value (non-null) for that question
      - mode="ge1":   count of respondents with GP_Visits >= 1 for that question
      - mode="sum":   sum of GP_Visits for that CF category (total visits)
    """

    # header labels
    col_labels = []
    for q in util_qcodes:
        meta = util_question_meta.get(q, {})
        col_labels.append(f"{q}: {meta.get('title', q)}")

    # styles (Excel-grid look)
    th_style = {
        "border": "1px solid #000",
        "padding": "8px",
        "textAlign": "left",
        "verticalAlign": "middle",
        "fontWeight": "bold",
        "backgroundColor": "#f5f5f5",
    }
    td_left = {
        "border": "1px solid #000",
        "padding": "8px",
        "textAlign": "left",
        "verticalAlign": "middle",
        "fontWeight": 500,
    }
    td_center = {
        "border": "1px solid #000",
        "padding": "8px",
        "textAlign": "center",
        "verticalAlign": "middle",
    }

    # Build a working copy so we don't mutate upstream df_demo
    base = df_demo.copy()

    # Precompute GP_Visits columns per question once
    gp_cols = {}
    for q in util_qcodes:
        out_col = f"{q}_GP_Visits"
        base = build_gp_visits(base, source_col=q, out_col=out_col)
        gp_cols[q] = out_col

    # Build body rows
    body_rows = []
    for cat in category_order:
        row_cells = [html.Td(category_labels.get(cat, str(cat)), style=td_left)]

        cat_mask = base[cf_col].eq(cat)

        for q in util_qcodes:
            gp_col = gp_cols[q]
            sub = base.loc[cat_mask, gp_col]

            if mode == "valid":
                val = int(sub.notna().sum())
            elif mode == "ge1":
                val = int((sub.fillna(0) >= 1).sum())
            elif mode == "sum":
                val = int(sub.fillna(0).sum())
            else:
                raise ValueError("mode must be one of: 'valid', 'ge1', 'sum'")

            row_cells.append(html.Td(str(val), style=td_center))

        body_rows.append(html.Tr(row_cells))

    # Header
    thead = html.Thead(
        html.Tr(
            [html.Th("Category", style=th_style)]
            + [html.Th(lbl, style=th_style) for lbl in col_labels]
        )
    )

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
