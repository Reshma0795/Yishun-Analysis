from dash import html
import pandas as pd
from typing import Dict, List, Tuple
from logic.utilization_helpers import build_gp_visits


def build_cf_x_utilization_binned_tables_per_question(
    df_demo: pd.DataFrame,
    *,
    cf_col: str,
    category_order: List,
    category_labels: Dict,
    util_qcodes: List[str],
    util_question_meta: Dict,
    title_prefix: str = "CF × Healthcare Utilization",
    show_pct: bool = True,
    pct_decimals: int = 1,
    bins: Tuple[int, int] = (2, 5),  # 1–2, 3–5, 6+
):

    bin_labels = [
        "Total (N=2499)",
        "0 visits",
        "1–2 visits",
        "3–5 visits",
        "6+ visits",
    ]

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
        "padding": "10px 8px",
        "textAlign": "center",
        "verticalAlign": "middle",
        "whiteSpace": "pre-line",
        "lineHeight": "1.25",
    }

    base = df_demo.copy()

    # ✅ Overall N for the CF (matches your CF matrix "Total" denominator)
    overall_mask = base[cf_col].isin(category_order)
    overall_n = int(overall_mask.sum())

    def to_bin(v):
        # Missing -> 0 visits
        if pd.isna(v):
            v = 0

        try:
            v = float(v)
        except Exception:
            v = 0

        # Impute refused/unable to recall -> 0
        if v in (666, 777):
            v = 0.0

        if v <= 0:
            return "0 visits"
        if 1 <= v <= bins[0]:
            return "1–2 visits"
        if (bins[0] + 1) <= v <= bins[1]:
            return "3–5 visits"
        return "6+ visits"

    components = []

    for q in util_qcodes:
        out_col = f"{q}_GP_Visits"
        base_q = build_gp_visits(base.copy(), source_col=q, out_col=out_col)

        meta = util_question_meta.get(q, {})
        q_title = meta.get("title", q)

        thead = html.Thead(
            html.Tr(
                [html.Th("Category", style=th_left)]
                + [html.Th(b, style=th_style) for b in bin_labels]
            )
        )

        body_rows = []
        for cat in category_order:
            cat_mask = base_q[cf_col].eq(cat)
            n_cat = int(cat_mask.sum())  # ✅ CF category total (for Total column)

            # bin assignment (always returns a string, so no need for dropna)
            sub = base_q.loc[cat_mask, out_col].apply(to_bin)
            denom = int(len(sub))  # denom for bin-% within this CF row
            counts = sub.value_counts().to_dict()

            row_cells = [html.Td(category_labels.get(cat, str(cat)), style=td_left)]

            # ✅ Total column uses % of overall sample, not 100%
            if show_pct:
                pct_total = (n_cat / overall_n * 100) if overall_n > 0 else 0.0
                total_cell = html.Div(
                    [
                        html.Div(
                            f"{pct_total:.{pct_decimals}f}%",
                            style={"fontWeight": "600", "fontSize": "14px", "marginBottom": "4px"},
                        ),
                        html.Div(f"(n={n_cat})", style={"fontSize": "11px", "color": "#666"}),
                    ]
                )
            else:
                total_cell = str(n_cat)

            row_cells.append(html.Td(total_cell, style=td_center))

            # Bin columns remain % within CF-row
            for b in bin_labels[1:]:
                n = int(counts.get(b, 0))
                if show_pct:
                    pct = (n / denom * 100) if denom > 0 else 0.0
                    cell = html.Div(
                        [
                            html.Div(
                                f"{pct:.{pct_decimals}f}%",
                                style={"fontWeight": "600", "fontSize": "14px", "marginBottom": "4px"},
                            ),
                            html.Div(f"(n={n})", style={"fontSize": "11px", "color": "#666"}),
                        ]
                    )
                else:
                    cell = str(n)

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

        components.append(
            html.Div(
                [
                    html.H4(f"{q}: {q_title}", style={"marginTop": "12px"}),
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
        )

    # ✅ 3 tables per row
    def chunk(lst, n):
        for i in range(0, len(lst), n):
            yield lst[i : i + n]

    rows = []
    for row_items in chunk(components, 2):
        rows.append(
            html.Div(
                [
                    html.Div(item, style={"flex": "1 1 0", "minWidth": "320px"})
                    for item in row_items
                ],
                style={
                    "display": "flex",
                    "gap": "16px",
                    "alignItems": "flex-start",
                    "marginBottom": "16px",
                },
            )
        )

    return html.Div([html.H3(title_prefix), *rows])
