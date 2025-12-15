import pandas as pd
from dash import html, dash_table, dcc
import plotly.express as px

# Reuse your existing GI logic so rules stay consistent (no duplication)
from logic.global_impressions import (
    gi_i_flag,
    gi_ii_flag,
    gi_iii_flag,
    gi_iv_flag,
    gi_v_flag,  # currently placeholder False in your file
)

# ============================================================
# 1) Assign exactly 1 GI per person (single-label classification)
# ============================================================
GI_ORDER = ["GI I", "GI II", "GI III", "GI IV", "GI V", "Unclassified"]

def assign_gi_label(row) -> str:
    """
    Single GI assignment per person using a priority order.
    This prevents overlap (a person won't appear in multiple GIs).
    """
    if gi_iv_flag(row):
        return "GI IV"
    if gi_v_flag(row):
        return "GI V"
    if gi_iii_flag(row):
        return "GI III"
    if gi_ii_flag(row):
        return "GI II"
    if gi_i_flag(row):
        return "GI I"
    return "Unclassified"


def build_gi_assigned_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Separate DF used only for GI vs CF tables (not utilisation).
    """
    dff = df.copy()
    dff["GI_Assigned"] = dff.apply(assign_gi_label, axis=1)
    dff["GI_Assigned"] = pd.Categorical(dff["GI_Assigned"], categories=GI_ORDER, ordered=True)
    return dff

# ============================================================
# 2) Configure your CFs here (15 CFs)
#    Replace `col` with the *actual* dataset column name for each CF.
# ============================================================
CF_CONFIG = [
    {
        "key": "functional_assessment",
        "title": "A. Functional Assessment",
        "col": "Functional_Assessment",
        "value_map": {
        0: "No deficit",
        1: "any IADL deficit, no ADL deficit",
        2: "Any ADL deficit",
    },
    },
    {
    "key": "nursing_needs",
    "title": "B. Nursing type skilled task needs",
    "col": "Nursing_Needs",
    "value_map": {
        0: "none",
        1: "moderate (1 task)",
        2: "high (2 or more tasks)",
    },
    },
    {
        "key": "rehab_needs",
        "title": "C. Rehabilitation needs",
        "col": "Rehab_Needs",
        "value_map": {
            0: "none",
            1: "moderate (1 task)",
            2: "high (2 or more tasks)",
        },
    },
    {
        "key": "activation_own_care",
        "title": "D. Activation of own care",
        "col": "Activation_Care",
        "value_map": {
            0: "ready, understands and interested in treatment; active cooperation and participative",
            1: "unsure but willing to cooperate, can be expected to provide at least a moderate level of self-care",
            2: "major disconnect, unaware/ no insight, may be defiant and can't be expected to provide even a modest level of self-care",
        },
    },
    {
        "key": "organization_of_care",
        "title": "D. Organization of care",
        "col": "Organization_of_Care_CF",
        "value_map": {
            0: "patient will see no more than 1 doctor, from 1 site of care",
            1: "patient will see more than 1 doctor, from 1 site of care",
            2: "patient will see more than 1 doctor, from more than 1 site of care",
        },
    },
    # =========================================================
    # F. Disruptive behavioural issues (0/1/2)
    # =========================================================
    {
        "key": "disruptive_behaviour",
        "title": "F. Disruptive behavioural issues",
        "col": "Disruptive_Behaviour",
        "value_map": {
            0: "None",
            1: "1 or more not significantly affecting care",
            2: "1 or more significantly affecting care",
        },
    },
    # =========================================================
    # G. Social support in case of need (0/1/2)
    # =========================================================
    {
        "key": "social_support",
        "title": "G. Social support in case of need",
        "col": "Social_Support_CF", 
        "value_map": {
            0: "has support for both basic healthcare services and companionship",
            1: "no support for basic healthcare services but companionship",
            2: "has no support",
        },
    },
    # =========================================================
    # H. Hospital admissions in last 6 months (0/1/2)
    # =========================================================
    {
        "key": "hospital_admission",
        "title": "H. Hospital admissions in last 6 months",
        "col": "Hospital_Admissions_CF", 
        "value_map": {
            0: "none",
            1: "1 or 2",
            2: "3 or more",
        },
    },

    # =========================================================
    # I. Polypharmacy (0/1/2)
    # =========================================================
    {
        "key": "polypharmacy",
        "title": "I. Polypharmacy",
        "col": "Polypharmacy_CF",
        "value_map": {
            0: "fewer than 5 prescription medications",
            1: "5 to 8 prescription medications",
            2: "9 or more prescription medications",
        },
    },

    # =========================================================
    # J. Financial Challenges (0/1)
    # =========================================================
    {
        "key": "financial_challenges",
        "title": "J. Financial Challenges",
        "col": "Financial_Challenges_CF",  # <-- change
        "value_map": {
            0: "no",
            1: "yes",
        },
    },

    # =========================================================
    # K. Specialist medical service needs (0/1/2)
    # =========================================================
    {
        "key": "specialist_service",
        "title": "K. Specialist medical service needs",
        "col": "Specialist_Medical_Service_Needs_CF",
        "value_map": {
            0: "no need",
            1: "single or occasional referral for advice to the primary physician",
            2: "regular follow up by specialist(s) for ongoing care of a condition",
        },
    },

    # =========================================================
    # L. Non-medical resource needs (0/1/2)
    # =========================================================
    {
        "key": "non_medical_resource",
        "title": "L. Non-medical resource needs",
        "col": "Non_Medical_Resource_Needs_CF",
        "value_map": {
            0: "has stable and secure access to all areas of social determinants of health",
            1: "has some, intermittent concerns with at least one area of social determinants of health",
            2: "has major ongoing problems with at least one area of social determinants of health",
        },
    },
]


# ============================================================
# 3) Helpers to build Crosstab tables
# ============================================================
def _coerce_cf_series(series: pd.Series, value_map=None) -> pd.Series:
    s = series.copy()

    # normalize numeric strings -> numbers
    s_num = pd.to_numeric(s, errors="coerce")
    s = s.where(s_num.isna(), s_num)  # replace where numeric

    # remove special codes
    s = s.replace({777: pd.NA, 888: pd.NA, 999: pd.NA})

    # map codes -> labels
    if value_map:
        def _map(v):
            if pd.isna(v):
                return pd.NA
            try:
                v_int = int(v)
                return value_map.get(v_int, v_int)
            except Exception:
                return value_map.get(v, v)
        s = s.map(_map)

    return s


def build_gi_cf_crosstab(dff: pd.DataFrame, cf_col: str, value_map=None) -> pd.DataFrame:
    tmp = dff[[cf_col, "GI_Assigned"]].copy()
    tmp[cf_col] = _coerce_cf_series(tmp[cf_col], value_map=value_map)
    tmp = tmp[tmp[cf_col].notna()].copy()
    ct = pd.crosstab(
        index=tmp[cf_col].astype("string"),
        columns=tmp["GI_Assigned"],
        dropna=False)
    for gi in GI_ORDER:
        if gi not in ct.columns:ct[gi] = 0
    ct = ct[GI_ORDER]
    ct["Total"] = ct.sum(axis=1)
    ct = ct.sort_values("Total", ascending=False)
    ct = ct.reset_index().rename(columns={cf_col: "CF_Value"})
    return ct

def make_datatable(df_ct: pd.DataFrame):
    return dash_table.DataTable(
        data=df_ct.to_dict("records"),
        columns=[{"name": c, "id": c} for c in df_ct.columns],
        page_size=15,
        sort_action="native",
        style_table={"overflowX": "auto"},
        style_cell={
            "textAlign": "center",
            "padding": "6px",
            "whiteSpace": "normal",
            "height": "auto",
            "fontSize": "13px",
        },
        style_header={"backgroundColor": "#f0f0f0", "fontWeight": "bold"},
    )
def make_heatmap_from_crosstab(df_ct: pd.DataFrame, ignore_missing: bool = True):
    """
    df_ct is the output of build_gi_cf_crosstab():
      columns: CF_Value, GI I..GI V, Unclassified, Total

    Heatmap uses:
      y = CF_Value
      x = GI categories
      z = counts
    """
    gi_cols = [c for c in GI_ORDER if c in df_ct.columns]
    plot_df = df_ct.copy()

    # Optionally drop Missing row (as you requested)
    if ignore_missing:
        plot_df = plot_df[plot_df["CF_Value"] != "Missing"].copy()

    # If nothing left after dropping Missing, return a message instead of breaking
    if plot_df.empty:
        return html.Div("No non-missing values to plot.", style={"color": "#b00020"})

    # Build matrix for px.imshow
    z = plot_df[gi_cols].values
    x = gi_cols
    y = plot_df["CF_Value"].astype(str).tolist()

    fig = px.imshow(
        z,
        x=x,
        y=y,
        text_auto=True,          # shows counts in each cell
        aspect="auto",
    )

    fig.update_layout(
        title = None,
        margin=dict(l=80, r=30, t=60, b=40),
        xaxis_title="Global Impression (Assigned)",
        yaxis_title="CF category",
        height=max(420, 40 * len(y)),  # auto-grow with number of CF categories
    )

    return dcc.Graph(figure=fig, config={"displayModeBar": False})


# ============================================================
# 4) Dash layout for the new GI vs CF page (TABLES)
# ============================================================
def layout(df: pd.DataFrame):
    dff = build_gi_assigned_df(df)

    blocks = []
    for item in CF_CONFIG:
        title = item["title"]
        col = item["col"]
        heatmap_col = item.get("heatmap_col", col)   # default: same as table col

        # ----- Table (non-imputed) -----
        if col not in dff.columns:
            blocks.append(html.H4(title, style={"marginTop": "18px"}))
            blocks.append(html.Div(f"Column '{col}' not found in dataframe.",
                                style={"color": "#b00020", "marginBottom": "10px"}))
        else:
            ct_table = build_gi_cf_crosstab(dff, col, value_map=item.get("value_map"))
            blocks.append(html.H4(title, style={"marginTop": "18px"}))
            blocks.append(make_datatable(ct_table))

        # ----- Heatmap (imputed where specified) -----
        if heatmap_col not in dff.columns:
            blocks.append(html.Div(f"Heatmap column '{heatmap_col}' not found in dataframe.",
                                style={"color": "#b00020", "marginBottom": "10px"}))
        else:
            ct_heat = build_gi_cf_crosstab(dff, heatmap_col, value_map=item.get("value_map"))
            blocks.append(make_heatmap_from_crosstab(ct_heat, ignore_missing=True))


    return html.Div(
        [
            html.H3("Distribution of # of CFs by Global Impression"),
            html.Div(blocks),
        ],
        style={"padding": "16px"},
    )
