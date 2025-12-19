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
    title: str = "Complicating Factor (%, n)",
    pct_decimals: int = 1,
    total_denominator: Optional[int] = None,  # kept for signature, not used now
):
    """
    Table layout:

      - Rows: CF categories (0/1/2)
      - Columns:
          * Age groups (each with N in header)
          * Gender groups (each with N in header)
          * Ethnicity groups (each with N in header)

      Cell logic for any subgroup G (e.g. AgeBin = "<40"):

          Percent(CF = k | G) =
              (# respondents in group G with CF = k)
              / (total # respondents in group G) * 100

      So each column is *column-wise normalised* by total people in that bin.

      NOTE: The previous "Total (N=...)" column is removed.
    """

    if age_levels is None:
        age_levels = ["<40", "40–65", "65–85", ">=85"]
    if gender_levels is None:
        gender_levels = ["Male", "Female"]
    if eth_levels is None:
        eth_levels = ["Chinese", "Malay", "Indian", "Others"]

    # ---------- GROUP TOTALS (denominators for column-wise %) ----------
    # Age totals: everyone in that age bin, regardless of CF
    age_totals = (
        df_demo[df_demo[age_col].isin(age_levels)]
        .groupby(age_col)
        .size()
        .reindex(age_levels, fill_value=0)
        .to_dict()
    )

    # Gender totals
    gender_totals = (
        df_demo[df_demo[gender_col].isin(gender_levels)]
        .groupby(gender_col)
        .size()
        .reindex(gender_levels, fill_value=0)
        .to_dict()
    )

    # Ethnicity totals
    eth_totals = (
        df_demo[df_demo[eth_col].isin(eth_levels)]
        .groupby(eth_col)
        .size()
        .reindex(eth_levels, fill_value=0)
        .to_dict()
    )

    # ---------- Styles ----------
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
        """Cell with percent (column-wise) and n."""
        if denom is None or denom <= 0:
            return html.Td("—", style=td_center)
        pct = (n / denom) * 100
        return html.Td(
            [
                html.Div(
                    f"{pct:.{pct_decimals}f}%",
                    style={
                        "fontWeight": "600",
                        "fontSize": "14px",
                        "marginBottom": "6px",
                    },
                ),
                html.Div(f"(n={n})", style={"fontSize": "11px", "color": "#666"}),
            ],
            style=td_center,
        )

    # ---------- Header ----------
    thead = html.Thead(
        [
            # Row 1: big group headers
            html.Tr(
                [
                    html.Th("Category", style=th_left),
                    html.Th("Age Group (years)", colSpan=len(age_levels), style=th_style),
                    html.Th("Gender", colSpan=len(gender_levels), style=th_style),
                    html.Th("Ethnicity", colSpan=len(eth_levels), style=th_style),
                ]
            ),
            # Row 2: bins with N per bin
            html.Tr(
                [
                    html.Th("", style=th_left),
                    *[
                        html.Th(f"{a} (N={age_totals.get(a, 0)})", style=th_style)
                        for a in age_levels
                    ],
                    *[
                        html.Th(f"{g} (N={gender_totals.get(g, 0)})", style=th_style)
                        for g in gender_levels
                    ],
                    *[
                        html.Th(f"{e} (N={eth_totals.get(e, 0)})", style=th_style)
                        for e in eth_levels
                    ],
                ]
            ),
        ]
    )

    # ---------- Body ----------
    body_rows = []

    for cat in category_order:
        cat_mask = df_demo[cf_col].eq(cat)

        row_cells = [html.Td(category_labels.get(cat, str(cat)), style=td_left)]

        # Age columns: column-wise %
        for a in age_levels:
            n = int((cat_mask & (df_demo[age_col] == a)).sum())
            denom_age = age_totals.get(a, 0)
            row_cells.append(td_pct_n(n, denom_age))

        # Gender columns: column-wise %
        for g in gender_levels:
            n = int((cat_mask & (df_demo[gender_col] == g)).sum())
            denom_gender = gender_totals.get(g, 0)
            row_cells.append(td_pct_n(n, denom_gender))

        # Ethnicity columns: column-wise %
        for e in eth_levels:
            n = int((cat_mask & (df_demo[eth_col] == e)).sum())
            denom_eth = eth_totals.get(e, 0)
            row_cells.append(td_pct_n(n, denom_eth))

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
