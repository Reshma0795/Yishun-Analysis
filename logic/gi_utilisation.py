import pandas as pd
from dash import html, dcc
import plotly.express as px
from logic.global_impressions import gi_iv_flag  # your existing GI IV helper
from logic.global_impressions import assign_gi_label

UTIL_QS = ["Q78", "Q85", "Q91", "Q93", "Q96", "Q103"]

GI_ORDER = ["GI I", "GI II", "GI III", "GI IV", "Unclassified"]
BIN_ORDER = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11+"]

# --- same lists you used in global_impressions.py ---
GI_II_NLT_COLS = [
    "Q130_G", "Q130_J", "Q130_K", "Q130_L",
    "Q130_O", "Q130_P", "Q130_Q",
    "Q130_S", "Q130_T", "Q130_U",
    "Q130_V", "Q130_W",
]

GI_III_LT_COLS = [
    "Q130_A", "Q130_B", "Q130_C", "Q130_D",
    "Q130_E", "Q130_F", "Q130_H", "Q130_I",
    "Q130_M",
]


def bin_util_value(v):
    if pd.isna(v):
        return None
    try:
        iv = int(v)
    except (TypeError, ValueError):
        return None

    if iv <= 0:
        return "0"
    if 1 <= iv <= 10:
        return str(iv)
    return "11+"

def gi_by_question_counts_faceted(df: pd.DataFrame, question_col: str, title: str = None):
    dff = df.copy()
    dff["GI_Label"] = dff.apply(assign_gi_label, axis=1)

    binned_col = f"{question_col}_BIN"
    dff[binned_col] = dff[question_col].apply(bin_util_value)
    dff = dff[dff[binned_col].notna()].copy()

    tmp = (
        dff.groupby(["GI_Label", binned_col])
           .size()
           .reset_index(name="Count")
    )

    tmp["GI_Label"] = pd.Categorical(tmp["GI_Label"], categories=GI_ORDER, ordered=True)
    tmp[binned_col] = pd.Categorical(tmp[binned_col], categories=BIN_ORDER, ordered=True)
    tmp = tmp.sort_values(["GI_Label", binned_col])

    fig = px.bar(
        tmp,
        x=binned_col,
        y="Count",
        facet_row="GI_Label",
        category_orders={"GI_Label": GI_ORDER, binned_col: BIN_ORDER},
        title=title or f"{question_col}: Counts by GI",
        text="Count",
    )

    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(
        height=900,
        bargap=0.2,
        showlegend=False,
        margin=dict(l=60, r=40, t=70, b=60),
        xaxis_title=f"{question_col} (binned: 0, 1–10, 11+)",
        yaxis_title="Number of respondents",
    )
    fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
    return fig

def layout(df: pd.DataFrame):
    charts = []
    for q in UTIL_QS:
        if q in df.columns:
            charts.append(
                dcc.Graph(
                    figure=gi_by_question_counts_faceted(df, q, f"{q}: utilisation counts split by GI")
                )
            )

    return html.Div([
        html.H3("Healthcare utilisation (counts) split by Global Impression"),
        html.P("Each subplot is one GI category. X-axis: utilisation buckets. Y-axis: counts."),
        html.Div(charts)
    ], style={"padding": "16px"})
