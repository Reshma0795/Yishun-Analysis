from dash import html
import pandas as pd
from typing import Dict, List, Optional, Tuple

from logic.utilization_helpers import build_gp_visits


def build_cf_x_utilization_binned_table(
    df_demo: pd.DataFrame,
    *,
    cf_col: str,
    category_order: List,
    category_labels: Dict,
    util_qcodes: List[str],
    util_question_meta: Dict,   # HEALTHCARE_UTILIZATION_QUESTIONS
    title: str = "CF × Healthcare Utilization (0 / 1–2 / 3–5 / 6+)",
    show_pct: bool = True,      # show "pct%" under count
    pct_decimals: int = 1,
    bins: Tuple[int, int, int] = (2, 5, 6),  # 1–2, 3–5, 6+ (threshold start for 6+)
):
    """
    Builds an Excel-style table:
      Rows: CF categories
      Columns: each utilization question, split into bins: 0, 1–2, 3–5, 6+

    Cell shows:
      - if show_pct=True:  <count>\n(<pct>%)
      - else:              <count>

    Percentages are computed column-wise WITHIN each (CF category × question),
    i.e. for a fixed row and question: bins sum to 100%.
    """

    # Bin labels (fixed)
    bin_labels = ["0", "1–2", "3–5", "6+"]

    # Styles (Excel-grid look)
    th_style = {
        "border": "1px solid #000",
        "padding": "8px",
        "textAlign": "center",
        "verticalAlign": "middle",
        "fontWeight": "bold",
        "backgroundColor": "#f5f5f5",
        "whiteSpace": "normal",
    }
    th_left_style = {**th_style, "textAlign": "left"}

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
        "padding": "10px 8px",
        "textAlign": "center",
        "verticalAlign": "middle",
        "whiteSpace": "pre-line",  # allow line breaks
        "lineHeight": "1.25",
    }

    base = df_demo.copy()

    # Precompute numeric GP_Visits columns once per question
    gp_cols = {}
    for q in util_qcodes:
        out_col = f"{q}_GP_Visits"
        base = build_gp_visits(base, source_col=q, out_col=out_col)
        gp_cols[q] = out_col

    # Helper: map visits -> bin label
    # 0 -> "0"
    # 1-2 -> "1–2"
    # 3-5 -> "3–5"
    # >=6 -> "6+"
    def to_bin(v):
        if pd.isna(v):
            return None  # treat missing as missing (excluded from row totals)
        try:
            v = float(v)
        except Exception:
            return None
        if v <= 0:
            return "0"
        if 1 <= v <= bins[0]:
            return "1–2"
        if (bins[0] + 1) <= v <= bins[1]:
            return "3–5"
        return "6+"

    # ----- HEADER (2 rows) -----
    # Row 1: Category + each question spanning 4 columns
    row1 = [html.Th("Category", rowSpan=2, style=th_left_style)]
    for q in util_qcodes:
        meta = util_question_meta.get(q, {})
        q_title = meta.get("title", q)
        row1.append(
            html.Th(f"{q}: {q_title}", colSpan=4, style=th_style)
        )

    # Row 2: subheaders for bins
    row2 = []
    for _ in util_qcodes:
        for b in bin_labels:
            row2.append(html.Th(b, style=th_style))

    thead = html.Thead([html.Tr(row1), html.Tr(row2)])

    # ----- BODY -----
    body_rows = []
    for cat in category_order:
        cat_mask = base[cf_col].eq(cat)
        row_cells = [html.Td(category_labels.get(cat, str(cat)), style=td_left)]

        for q in util_qcodes:
            gp_col = gp_cols[q]
            sub = base.loc[cat_mask, gp_col].apply(to_bin)

            # Drop missing utilization for this question in this CF category
            sub = sub.dropna()

            denom = int(len(sub))  # denominator for % within this CF×question
            counts = sub.value_counts().to_dict()

            for b in bin_labels:
                n = int(counts.get(b, 0))
                if not show_pct:
                    cell = str(n)
                else:
                    pct = (n / denom * 100) if denom > 0 else 0.0
                    cell = f"{n}\n({pct:.{pct_decimals}f}%)"

                row_cells.append(html.Td(cell, style=td_center))

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
            html.Div(
                "Note: Percentages are within each (CF category × question) across the four bins; missing utilization values are excluded.",
                style={"color": "#666", "fontSize": "12px", "marginTop": "8px"},
            ),
        ]
    )
