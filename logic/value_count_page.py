# logic/gp_value_counts_page.py
import pandas as pd
from dash import html, dcc, dash_table
import dash_bootstrap_components as dbc
import plotly.express as px

from logic.value_counts_helpers import (
    build_value_counts_table,
    build_descriptive_stats_table,
    build_numeric_distribution_table,
)
from logic.question_texts import HEALTHCARE_UTILIZATION_QUESTIONS

QUESTIONS = ["Q78", "Q85", "Q91", "Q93", "Q96", "Q103"]

# Demographics question codes
AGE_COL = "Q2"
ETHNICITY_COL = "Q3"
GENDER_COL = "Q4"

# Codes to EXCLUDE from stats / charts
INVALID_CODES = {777, 888, 999}

# Optional: map common gender coding to labels (adjust if your dataset differs)
GENDER_LABEL_MAP = {1: "Male", 2: "Female"}


def _datatable(df, page_size=20):
    return dash_table.DataTable(
        data=df.to_dict("records"),
        columns=[{"name": c, "id": c} for c in df.columns],
        style_cell={
            "textAlign": "left",
            "padding": "10px",
            "fontFamily": "monospace",
            "fontSize": "14px",
            "border": "1px solid #e6e6e6",
        },
        style_header={
            "fontWeight": "bold",
            "backgroundColor": "#5b3fd3",
            "color": "white",
            "border": "1px solid #5b3fd3",
        },
        style_table={
            "borderRadius": "12px",
            "overflow": "hidden",
        },
        page_size=page_size,
    )


def _clean_series_for_chart(s: pd.Series, invalid_codes=INVALID_CODES, include_missing=True):
    s2 = s.copy()
    s2 = pd.to_numeric(s2, errors="ignore")

    if hasattr(s2, "isin"):
        s2 = s2[~s2.isin(list(invalid_codes))]

    if include_missing:
        s2 = s2.fillna("Missing")
    else:
        s2 = s2.dropna()

    return s2


def _pie_from_counts(counts: pd.Series, title: str):
    pie_df = counts.reset_index()
    pie_df.columns = ["Category", "Count"]
    fig = px.pie(pie_df, names="Category", values="Count", title=title)
    fig.update_traces(textinfo="percent+label")
    fig.update_layout(margin=dict(l=10, r=10, t=50, b=10), legend_title_text="")
    return fig


def _counts_table_from_series(s: pd.Series, title: str = None):
    counts = s.value_counts(dropna=False)
    out = counts.reset_index()
    out.columns = ["Category", "Count"]
    if title:
        out.insert(0, "Variable", title)
    return out


def _age_bins_series(df: pd.DataFrame, col=AGE_COL, include_missing=True):
    s = _clean_series_for_chart(df[col], include_missing=include_missing)
    s_num = pd.to_numeric(s.replace("Missing", pd.NA), errors="coerce")

    if s_num.notna().sum() > 0:
        bins = [-float("inf"), 39, 65, 85, float("inf")]
        labels = ["<40", "40–65", "65–85", "≥85"]

        binned = pd.cut(
            s_num,
            bins=bins,
            labels=labels,
            right=True,
            include_lowest=True,
        )

        if include_missing:
            binned = binned.astype("object").where(binned.notna(), "Missing")
        else:
            binned = binned.dropna()

        return binned

    # fallback: treat as categorical
    return s


def _age_pie(df: pd.DataFrame, col=AGE_COL, include_missing=True):
    if col not in df.columns:
        return None
    binned = _age_bins_series(df, col=col, include_missing=include_missing)
    counts = binned.value_counts(dropna=False)
    return _pie_from_counts(counts, "Age Distribution (Q2)")


def _simple_pie(df: pd.DataFrame, col: str, title: str, include_missing=True):
    if col not in df.columns:
        return None
    s = _clean_series_for_chart(df[col], include_missing=include_missing)
    counts = s.value_counts(dropna=False)
    return _pie_from_counts(counts, title)


def _gender_series_labeled(df: pd.DataFrame, col=GENDER_COL, include_missing=True):
    s = _clean_series_for_chart(df[col], include_missing=include_missing)

    # try numeric conversion for mapping
    s_num = pd.to_numeric(s.replace("Missing", pd.NA), errors="coerce")
    if s_num.notna().sum() > 0:
        labeled = s_num.map(GENDER_LABEL_MAP).astype("object")
        if include_missing:
            # keep any unmapped numeric values as their raw number
            labeled = labeled.where(labeled.notna(), s_num.astype("Int64").astype("object"))
            labeled = labeled.where(labeled.notna(), "Missing")
        else:
            labeled = labeled.dropna()
        return labeled

    # if not numeric, keep original values (e.g., already Male/Female)
    return s


def ValueCounts_layout(df: pd.DataFrame):
    # ----------------------------
    # Demographics pies + tables
    # ----------------------------
    fig_age = _age_pie(df, AGE_COL, include_missing=True)
    fig_gender = _simple_pie(df, GENDER_COL, "Gender (Q4)", include_missing=True)
    fig_eth = _simple_pie(df, ETHNICITY_COL, "Ethnicity (Q3)", include_missing=True)

    # Build count tables (dataframes)
    age_table_df = None
    gender_table_df = None
    eth_table_df = None

    if AGE_COL in df.columns:
        age_bins = _age_bins_series(df, AGE_COL, include_missing=True)
        age_table_df = _counts_table_from_series(age_bins)
    if GENDER_COL in df.columns:
        gender_labeled = _gender_series_labeled(df, GENDER_COL, include_missing=True)
        gender_table_df = _counts_table_from_series(gender_labeled)
    if ETHNICITY_COL in df.columns:
        eth_s = _clean_series_for_chart(df[ETHNICITY_COL], include_missing=True)
        eth_table_df = _counts_table_from_series(eth_s)

    demo_charts = dbc.Card(
        dbc.CardBody(
            [
                # Pie charts row
                dbc.Row(
                    [
                        dbc.Col(
                            dcc.Graph(figure=fig_age, config={"displayModeBar": False})
                            if fig_age else html.Div("Age (Q2) not found in dataset."),
                            md=4,
                        ),
                        dbc.Col(
                            dcc.Graph(figure=fig_gender, config={"displayModeBar": False})
                            if fig_gender else html.Div("Gender (Q4) not found in dataset."),
                            md=4,
                        ),
                        dbc.Col(
                            dcc.Graph(figure=fig_eth, config={"displayModeBar": False})
                            if fig_eth else html.Div("Ethnicity (Q3) not found in dataset."),
                            md=4,
                        ),
                    ],
                    className="g-2",
                ),

                html.Hr(),

                # Count tables row
                dbc.Row(
                    [
                        dbc.Col(
                            html.Div(
                                [
                                    html.H6("Age bins – Count table"),
                                    _datatable(age_table_df, page_size=10) if age_table_df is not None
                                    else html.Div("Age (Q2) not found in dataset."),
                                ]
                            ),
                            md=4,
                        ),
                        dbc.Col(
                            html.Div(
                                [
                                    html.H6("Gender – Count table"),
                                    _datatable(gender_table_df, page_size=10) if gender_table_df is not None
                                    else html.Div("Gender (Q4) not found in dataset."),
                                ]
                            ),
                            md=4,
                        ),
                        dbc.Col(
                            html.Div(
                                [
                                    html.H6("Ethnicity – Count table"),
                                    _datatable(eth_table_df, page_size=10) if eth_table_df is not None
                                    else html.Div("Ethnicity (Q3) not found in dataset."),
                                ]
                            ),
                            md=4,
                        ),
                    ],
                    className="g-2",
                ),
            ]
        ),
        style={
            "borderRadius": "16px",
            "boxShadow": "0 6px 18px rgba(0,0,0,0.08)",
            "marginBottom": "16px",
        },
    )

    # ----------------------------
    # Existing utilization blocks
    # ----------------------------
    value_count_blocks = []

    for q in QUESTIONS:
        q_meta = HEALTHCARE_UTILIZATION_QUESTIONS.get(q, {})

        vc_df = build_value_counts_table(df, q, include_missing=True, sort_numeric=True)
        stats_df = build_descriptive_stats_table(df, q, invalid_codes=INVALID_CODES)
        dist_df = build_numeric_distribution_table(df, q, invalid_codes=INVALID_CODES)

        value_count_blocks.append(
            dbc.Card(
                dbc.CardBody(
                    [
                        html.H4(f"{q} – {q_meta.get('title', '')}"),
                        html.P(q_meta.get("question", ""), style={"color": "#555"}),

                        html.H6("Descriptive statistics"),
                        dash_table.DataTable(
                            data=stats_df.to_dict("records"),
                            columns=[{"name": c, "id": c} for c in stats_df.columns],
                            style_cell={"textAlign": "center"},
                        ),

                        html.Hr(),

                        html.H6("Value counts"),
                        dash_table.DataTable(
                            data=vc_df.to_dict("records"),
                            columns=[{"name": c, "id": c} for c in vc_df.columns],
                            style_cell={
                                "textAlign": "left",
                                "padding": "10px",
                                "fontFamily": "monospace",
                            },
                            style_header={
                                "fontWeight": "bold",
                                "backgroundColor": "#5b3fd3",
                                "color": "white",
                            },
                        ),
                    ]
                ),
                style={
                    "borderRadius": "16px",
                    "boxShadow": "0 6px 18px rgba(0,0,0,0.08)",
                    "marginBottom": "16px",
                },
            )
        )

    return html.Div(
        [
            html.H2("Demographics"),
            demo_charts,
            html.H2("Healthcare Utilization – Value Counts + Descriptive Statistics"),
            *value_count_blocks,
        ],
        style={ "width": "100%", "margin": "0 auto"},
    )
