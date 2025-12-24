import pandas as pd
from dash import html, dcc, dash_table, Dash
import plotly.express as px
from logic.mapping_helpers import build_mapping_table
from logic.gi_table_helper import gi_one_row_table
from logic.gi_content import GI_CONTENT
import dash_bootstrap_components as dbc
import numpy as np
# ============================================================
# Constants
# ============================================================
GI_IV_S0_COL = "S0"
GI_IV_Q129_COL = "Q129"
GI_IV_Q142_COL = "Q142"
GI_IV_COG_COLS = [f"Q{i}" for i in range(16, 27)]   # Q16 → Q26

UTIL_QS = ["Q78", "Q85", "Q91", "Q93", "Q96", "Q103"]

# NEW: bins = 0, 1–2, 3–5, 6+
UTIL_BIN_ORDER = ["0", "1–2", "3–5", "6+"]

GI_II_NLT_COLS = [
    "Q130_G", "Q130_J", "Q130_K", "Q130_L", "Q130_O", "Q130_P",
    "Q130_Q", "Q130_S", "Q130_T", "Q130_U", "Q130_V", "Q130_W"
]
GI_III_LT_COLS = [
    "Q130_A", "Q130_B", "Q130_C", "Q130_D", "Q130_E",
    "Q130_F", "Q130_H", "Q130_I", "Q130_M"
]

GI_ORDER_SEVERE_TO_MILD = ["GI V", "GI IV", "GI III", "GI II", "GI I"]
GI_ORDER_FULL = ["GI I", "GI II", "GI III", "GI IV", "GI V", "Unclassified"]

UTIL_Q_TITLES = {
    "Q78":  "Q78 (Private GP visits) – Utilisation by GI Category",
    "Q85":  "Q85 (Polyclinic doctor visits) – Utilisation by GI Category",
    "Q91":  "Q91 (Specialist Outpatient Clinic visits) – Utilisation by GI Category",
    "Q93":  "Q93 (Emergency Department visits) – Utilisation by GI Category",
    "Q96":  "Q96 (Public hospital admissions) – Utilisation by GI Category",
    "Q103": "Q103 (Private hospital admissions) – Utilisation by GI Category",
}


# ============================================================
# Core helpers
# ============================================================
def _to_int(x):
    if pd.isna(x):
        return None
    try:
        return int(x)
    except (TypeError, ValueError):
        return None


def _map_cog_to_binary(v):
    v = _to_int(v)
    if v is None:
        return None
    if v == 1:
        return 1
    if v in (2, 777, 999):
        return 0
    return None


def gi_iv_flag(row) -> bool:
    s0 = _to_int(row.get(GI_IV_S0_COL))
    q129 = _to_int(row.get(GI_IV_Q129_COL))
    cond_1 = (s0 == 2) and (q129 == 1)

    q142 = _to_int(row.get(GI_IV_Q142_COL))
    cond_2 = (q142 is not None and q142 <= 2)

    cog_vals = [_map_cog_to_binary(row.get(c)) for c in GI_IV_COG_COLS if c in row.index]
    if len(cog_vals) == 0 or all(v is None for v in cog_vals):
        cond_3 = False
    else:
        cog_sum = sum((v if v is not None else 0) for v in cog_vals)
        cond_3 = (cog_sum < 5)

    score = int(cond_1) + int(cond_2) + int(cond_3)
    return score >= 2


def gi_i_flag(row) -> bool:
    healthy = (
        row.get("Q124") == 2 and
        row.get("Q126") == 2 and
        row.get("Q128") == 2 and
        row.get("Q129") == 2 and
        row.get("Q130") == 2
    )
    return healthy and (not gi_iv_flag(row))


def gi_ii_flag(row) -> bool:
    has_nlt = any(row.get(col, 0) == 1 for col in GI_II_NLT_COLS)
    has_elevated_bp = row.get("Q124") in (1, 3)
    not_limited = row.get("Q142") == 3
    return (has_nlt or has_elevated_bp) or not_limited


def gi_iii_flag(row) -> bool:
    has_nlt = any(row.get(col, 0) == 1 for col in GI_II_NLT_COLS)
    has_elevated_bp = row.get("Q124") in (1, 3)
    q142 = row.get("Q142")
    limited = q142 == 1
    has_lt = any(row.get(col, 0) == 1 for col in GI_III_LT_COLS)
    not_limited = q142 == 3
    return ((has_nlt or has_elevated_bp) and limited) or (has_lt and not_limited)


def gi_v_flag(row) -> bool:
    """
    GI V logic:
      (Q96 >= 2 OR Q103 >= 2)  AND  (any life-threatening condition == 1)
    Notes:
      - Treats 666/777/888/999 and missing as 0 for hospitalization count.
      - Life-threatening cols are the GI_III_LT_COLS (Q130_A ... etc.).
    """
    def _safe_hosp(v):
        v = _to_int(v)
        if v is None:
            return 0
        if v in (666, 777, 888, 999):
            return 0
        return v

    q96 = _safe_hosp(row.get("Q96"))
    q103 = _safe_hosp(row.get("Q103"))
    has_2plus_hosp = (q96 >= 2) or (q103 >= 2)
    has_life_threatening = any(_to_int(row.get(col)) == 1 for col in GI_III_LT_COLS)
    return has_2plus_hosp and has_life_threatening


# ============================================================
# Assign ONE GI label per person (single classification)
# ============================================================
def compute_unique_gi_labels(df: pd.DataFrame) -> pd.Series:
    """
    Returns ONE GI label per row by severity:
      GI V > GI IV > GI III > GI II > GI I > Unclassified
    """
    idx = df.index
    out = pd.Series("Unclassified", index=idx, dtype="object")

    # Raw masks (can overlap)
    m5 = df.apply(gi_v_flag, axis=1).fillna(False)
    m4 = df.apply(gi_iv_flag, axis=1).fillna(False)
    m3 = df.apply(gi_iii_flag, axis=1).fillna(False)
    m2 = df.apply(gi_ii_flag, axis=1).fillna(False)

    healthy = (
        (df["Q124"] == 2) &
        (df["Q126"] == 2) &
        (df["Q128"] == 2) &
        (df["Q129"] == 2) &
        (df["Q130"] == 2)
    ).fillna(False)

    m1 = healthy & (~m4)  # GI I rule: healthy AND not GI IV

    # Severity precedence
    out.loc[m5] = "GI V"
    out.loc[m4 & ~m5] = "GI IV"
    out.loc[m3 & ~(m4 | m5)] = "GI III"
    out.loc[m2 & ~(m3 | m4 | m5)] = "GI II"
    out.loc[m1 & ~(m2 | m3 | m4 | m5)] = "GI I"

    return out


def add_unique_gi_column(df: pd.DataFrame, col_name: str = "GI_Assigned") -> pd.DataFrame:
    """
    Adds a categorical GI_Assigned column (GI I..V, Unclassified) if not present.
    """
    if col_name in df.columns:
        return df
    dff = df.copy()
    labels = compute_unique_gi_labels(dff)
    dff[col_name] = pd.Categorical(labels, categories=GI_ORDER_FULL, ordered=True)
    return dff


# ============================================================
# Stepwise escalation helpers
# ============================================================
def compute_stepwise_escalation_labels(df: pd.DataFrame):
    """
    Stepwise escalation (mild -> severe):
      Start at GI I, then promote overlaps to GI II, GI III, GI IV, GI V.
    """
    idx = df.index
    labels = pd.Series("Unclassified", index=idx, dtype="object")

    m5 = df.apply(gi_v_flag, axis=1).fillna(False)
    m4 = df.apply(gi_iv_flag, axis=1).fillna(False)
    m3 = df.apply(gi_iii_flag, axis=1).fillna(False)
    m2 = df.apply(gi_ii_flag, axis=1).fillna(False)

    healthy = (
        (df["Q124"] == 2) &
        (df["Q126"] == 2) &
        (df["Q128"] == 2) &
        (df["Q129"] == 2) &
        (df["Q130"] == 2)
    ).fillna(False)

    m1 = healthy & (~m4)

    labels.loc[m1] = "GI I"

    steps = []

    def _step_promote(from_labels, to_label, to_mask):
        promotable = labels.isin(from_labels) & to_mask
        n_promoted = int(promotable.sum())
        labels.loc[promotable] = to_label
        n_after = int((labels == to_label).sum())

        steps.append({
            "Step": f"{'/'.join(from_labels)} → {to_label}",
            "Promoted this step": n_promoted,
            "Total now in target": n_after,
        })

    _step_promote(["GI I"], "GI II", m2)
    _step_promote(["GI I", "GI II"], "GI III", m3)
    _step_promote(["GI I", "GI II", "GI III"], "GI IV", m4)
    _step_promote(["GI I", "GI II", "GI III", "GI IV"], "GI V", m5)

    summary = pd.DataFrame(steps)
    return labels, summary


# ============================================================
# Stepwise escalation chart helpers
# ============================================================
def gi_stepwise_escalation_chart(df: pd.DataFrame):
    labels, summary = compute_stepwise_escalation_labels(df)

    fig = px.bar(
        summary,
        x="Step",
        y="Promoted this step",
        text="Promoted this step",
        title="GI Stepwise Escalation (Mild → Severe): Overlaps promoted at each step",
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(
        xaxis_title="Stepwise Comparison",
        yaxis_title="Number of respondents promoted",
        margin=dict(l=30, r=30, t=70, b=80),
        height=480,
    )
    return fig


# ============================================================
# Distribution chart helpers
# ============================================================
def gi_unique_distribution_chart(df: pd.DataFrame):
    labels = compute_unique_gi_labels(df)
    order = ["GI I", "GI II", "GI III", "GI IV", "GI V", "Unclassified"]
    counts = labels.value_counts().reindex(order, fill_value=0).reset_index()
    counts.columns = ["GI", "Count"]
    fig = px.bar(
        counts,
        x="GI",
        y="Count",
        text="Count",
        category_orders={"GI": order},
    )
    counts["Pct"] = counts["Count"] / counts["Count"].sum() * 100
    fig.update_traces(
        text=[f"{c} ({p:.1f}%)" for c, p in zip(counts["Count"], counts["Pct"])],
        textposition="outside",
    )

    fig.update_layout(
        xaxis_title="GI Category",
        yaxis_title="Number of respondents",
        margin=dict(l=30, r=30, t=70, b=40),
        height=450,
        yaxis_type="log",
    )
    return fig


# ============================================================
# Utilisation binning (UPDATED: 0, 1–2, 3–5, 6+)
# ============================================================
def bin_util_value(v):
    """
    Bucket utilisation values to: 0, 1–2, 3–5, 6+.
    Non-numeric / NA -> None (excluded from chart).
    """
    if pd.isna(v):
        return None
    try:
        iv = int(v)
    except (TypeError, ValueError):
        return None

    if iv <= 0:
        return "0"
    if 1 <= iv <= 2:
        return "1–2"
    if 3 <= iv <= 5:
        return "3–5"
    return "6+"


# ============================================================
# GI × Utilisation helpers (TABLE + CHART)
# ============================================================
def gi_util_binned_table(df: pd.DataFrame, util_q: str, gi_col: str = "GI_Assigned") -> pd.DataFrame:
    """
    Builds a table: rows = GI category, columns = utilisation bins (0,1–2,3–5,6+), values = counts.
    """
    dff = add_unique_gi_column(df, gi_col)

    if util_q not in dff.columns:
        return pd.DataFrame()

    tmp = dff[[util_q, gi_col]].copy()
    tmp["UtilBin"] = tmp[util_q].apply(bin_util_value)
    tmp = tmp[tmp["UtilBin"].notna()]

    if tmp.empty:
        return pd.DataFrame()

    counts = (
        tmp.groupby([gi_col, "UtilBin"])
           .size()
           .reset_index(name="Count")
    )

    idx = pd.MultiIndex.from_product([GI_ORDER_FULL, UTIL_BIN_ORDER], names=[gi_col, "UtilBin"])
    counts = counts.set_index([gi_col, "UtilBin"]).reindex(idx, fill_value=0).reset_index()

    table = counts.pivot(index=gi_col, columns="UtilBin", values="Count").reset_index()
    table = table.rename(columns={gi_col: "GI Category"})
    return table


def gi_util_binned_chart(df: pd.DataFrame, util_q: str, gi_col: str = "GI_Assigned"):
    """
    Grouped bar chart: x = GI category, bars = utilisation bins, y = counts.
    """
    dff = add_unique_gi_column(df, gi_col)

    if util_q not in dff.columns:
        return None

    tmp = dff[[util_q, gi_col]].copy()
    tmp["UtilBin"] = tmp[util_q].apply(bin_util_value)
    tmp = tmp[tmp["UtilBin"].notna()]

    if tmp.empty:
        return None

    counts = (
        tmp.groupby([gi_col, "UtilBin"])
           .size()
           .reset_index(name="Count")
    )

    counts[gi_col] = pd.Categorical(counts[gi_col], categories=GI_ORDER_FULL, ordered=True)
    counts["UtilBin"] = pd.Categorical(counts["UtilBin"], categories=UTIL_BIN_ORDER, ordered=True)

    fig = px.bar(
        counts,
        x=gi_col,
        y="Count",
        color="UtilBin",
        barmode="group",
        text="Count",
        category_orders={gi_col: GI_ORDER_FULL, "UtilBin": UTIL_BIN_ORDER})

    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(
        xaxis_title="GI Category",
        yaxis_title="Number of respondents",
        legend_title="Utilisation bin",
        margin=dict(l=30, r=30, t=60, b=40),
        height=420,
    )
    return fig


def gi_utilisation_section(df: pd.DataFrame):
    """
    Builds a full section with:
      - For each utilisation question (Q78, Q85, Q91, Q93, Q96, Q103):
        * A table: GI × utilisation bins
        * A chart: grouped bar
    """
    dff = add_unique_gi_column(df)
    sections = []

    for q in UTIL_QS:
        if q not in dff.columns:
            continue

        table_df = gi_util_binned_table(dff, q)
        fig = gi_util_binned_chart(dff, q)

        if table_df.empty or fig is None:
            continue

        sections.append(
            html.Div(
                [
                    html.H4(UTIL_Q_TITLES[q]),

                    dash_table.DataTable(
                        data=table_df.to_dict("records"),
                        columns=[{"name": c, "id": c} for c in table_df.columns],
                        style_cell={"textAlign": "center"},
                        style_header={"fontWeight": "bold"},
                    ),
                    html.Br(),
                    dcc.Graph(figure=fig, config={"displayModeBar": False}),
                    html.Hr(),
                ]
            )
        )

    if not sections:
        return html.Div([html.P("No utilisation variables available for GI × utilisation analysis.")])

    return html.Div(sections)


def get_unique_gi_mask(df: pd.DataFrame, gi_label: str, gi_col: str = "GI_Assigned") -> pd.Series:
    """
    Returns a boolean mask for rows that are uniquely assigned to `gi_label`,
    using the same logic as the summary chart (highest severity wins).
    """
    dff = add_unique_gi_column(df, gi_col)
    return (dff[gi_col].astype(str) == gi_label).reindex(df.index).fillna(False)


def gi_count_bar_from_unique(df: pd.DataFrame, gi_label: str, gi_col: str = "GI_Assigned"):
    """
    Bar chart: In <GI> vs Others, using UNIQUE GI assignment.
    """
    mask = get_unique_gi_mask(df, gi_label, gi_col=gi_col)
    gi_count = int(mask.sum())
    total = int(len(df))

    count_table = pd.DataFrame(
        {"Group": [gi_label, "Others"], "Count": [gi_count, total - gi_count]}
    )

    fig = px.bar(
        count_table,
        x="Group",
        y="Count",
        text="Count",
    )
    return fig, mask


def gi_utilisation_section_individual_unique(df: pd.DataFrame, gi_label: str, gi_col: str = "GI_Assigned"):
    """
    Individual GI page utilisation section using UNIQUE GI assignment.

    For each utilisation question:
      - "In <gi_label>" vs "Others"
      - bins: 0, 1–2, 3–5, 6+
      - Table shows: Count + % within group (In GI vs Others)
      - Chart bars = Count, labels = Count + %
    """
    dff = add_unique_gi_column(df, gi_col)
    gi_mask = (dff[gi_col].astype(str) == gi_label).reindex(dff.index).fillna(False)

    sections = []

    for q in UTIL_QS:
        if q not in dff.columns:
            continue

        tmp = dff[[q]].copy()
        tmp["UtilBin"] = tmp[q].apply(bin_util_value)
        tmp = tmp[tmp["UtilBin"].notna()].copy()
        if tmp.empty:
            continue

        in_gi = gi_mask.reindex(tmp.index).fillna(False)
        in_label = f"In {gi_label}"
        tmp["Group"] = in_gi.map({True: in_label, False: "Others"})

        # ----- counts (complete grid) -----
        counts = (
            tmp.groupby(["UtilBin", "Group"])
               .size()
               .reset_index(name="Count")
        )

        full_index = pd.MultiIndex.from_product(
            [UTIL_BIN_ORDER, [in_label, "Others"]],
            names=["UtilBin", "Group"]
        )

        counts = (
            counts.set_index(["UtilBin", "Group"])
                  .reindex(full_index, fill_value=0)
                  .reset_index()
        )

        # ----- add % within each group -----
        group_totals = counts.groupby("Group")["Count"].transform("sum")
        counts["Pct"] = np.where(group_totals > 0, counts["Count"] / group_totals * 100, 0.0)
        counts["Label"] = counts.apply(lambda r: f"{int(r['Count'])} ({r['Pct']:.1f}%)", axis=1)

        # ensure ordering
        counts["UtilBin"] = pd.Categorical(counts["UtilBin"], categories=UTIL_BIN_ORDER, ordered=True)
        counts["Group"] = pd.Categorical(counts["Group"], categories=[in_label, "Others"], ordered=True)

        # ----- table: show "Count (Pct%)" in each bin cell -----
        table_df = (
            counts.pivot(index="Group", columns="UtilBin", values="Label")
                  .reindex([in_label, "Others"])
                  .reset_index()
        )
        table_df.columns.name = None

        # ----- chart: bars = Count, text = Label, hover includes both -----
        fig = px.bar(
            counts,
            x="UtilBin",
            y="Count",
            color="Group",
            barmode="group",
            text="Label",
            category_orders={"UtilBin": UTIL_BIN_ORDER},
            hover_data={"Count": True, "Pct":":.1f", "Label": False, "UtilBin": True, "Group": True},        )

        fig.update_traces(textposition="outside", cliponaxis=False)
        fig.update_layout(
            xaxis_title=f"{q} (binned)",
            yaxis_title="Number of respondents",
            legend_title="Group",
            margin=dict(l=30, r=30, t=60, b=40),
            height=380,
        )

        sections.append(
            html.Div(
                [
                    html.H4(UTIL_Q_TITLES.get(q, q)),

                    dash_table.DataTable(
                        data=table_df.to_dict("records"),
                        columns=[{"name": str(c), "id": str(c)} for c in table_df.columns],
                        style_cell={"textAlign": "center", "padding": "8px"},
                        style_header={"fontWeight": "bold"},
                        style_table={"overflowX": "auto"},
                    ),
                    html.Br(),
                    dcc.Graph(figure=fig, config={"displayModeBar": False}),
                    html.Hr(),
                ]
            )
        )

    if not sections:
        return html.Div([html.P(f"No utilisation variables available for {gi_label}.")])

    return html.Div(sections)


# ----------------------------
# Demographics constants
# ----------------------------
ETHNICITY_LABELS = {
    1: "Chinese",
    2: "Malay",
    3: "Indian",
    4: "Other",
    777: "Refused",
}

GENDER_LABELS = {
    1: "Male",
    2: "Female",
}

AGE_BIN_ORDER = ["<40", "40–65", "65–85", "≥85"]


def _to_int_safe(x):
    if pd.isna(x):
        return None
    try:
        return int(x)
    except (TypeError, ValueError):
        return None


def _age_bin_from_q2(v):
    """Bins for Q2: <40, 40–65, 65–85, ≥85. Returns None if invalid."""
    iv = _to_int_safe(v)
    if iv is None:
        return None
    if iv < 40:
        return "<40"
    if 40 <= iv <= 65:
        return "40–65"
    if 66 <= iv <= 85:
        return "65–85"
    return "≥85"


def _count_table(series, category_col="Category"):
    """Return a 2-col dataframe: Category, Count (sorted by count desc unless categorical order is set)."""
    s = series.dropna()
    if s.empty:
        return pd.DataFrame({category_col: [], "Count": []})

    # If series is categorical with order, respect it
    if pd.api.types.is_categorical_dtype(s):
        cats = list(s.cat.categories)
        counts = s.value_counts().reindex(cats, fill_value=0)
    else:
        counts = s.value_counts()

    df_counts = counts.reset_index()
    df_counts.columns = [category_col, "Count"]
    return df_counts


def _pie_from_counts(df_counts, title, category_order=None):
    """df_counts must have columns [Category, Count]."""
    if df_counts.empty:
        fig = px.pie(names=["No data"], values=[1], title=title)
        fig.update_traces(textinfo="none")
        return fig

    names_col = df_counts.columns[0]

    fig = px.pie(
        df_counts,
        names=names_col,
        values="Count",
        title=title,
        hole=0,
        category_orders={names_col: category_order} if category_order else None,
    )
    fig.update_traces(textposition="inside", textinfo="percent+label")
    fig.update_layout(margin=dict(l=10, r=10, t=40, b=10), height=320)
    return fig



def demographics_section_like_card(df: pd.DataFrame, title_suffix: str = ""):
    """
    Full demographics section:
      - Top: 3 pie charts (Age, Gender, Ethnicity)
      - Bottom: 3 count tables
    Excludes:
      - Ethnicity 777 (Refused)
      - Gender values not in {1,2}
    """
    # --- Age ---
    if "Q2" in df.columns:age_bins = df["Q2"].apply(_age_bin_from_q2)
    else: age_bins = pd.Series(index=df.index, dtype="object")
    age_bins = age_bins.astype("object")
    age_bins = pd.Series(pd.Categorical(age_bins, categories=AGE_BIN_ORDER, ordered=True), index=df.index, name="AgeBin")
    age_table = _count_table(age_bins, category_col="Category")
    age_fig = _pie_from_counts(age_table, f"Age Distribution{title_suffix}", category_order=AGE_BIN_ORDER)

    # --- Gender ---
    if "Q4" in df.columns:
        gender = df["Q4"].apply(_to_int_safe).map(GENDER_LABELS)
    else:
        gender = pd.Series(dtype="object")
    gender_table = _count_table(gender, category_col="Category")
    gender_fig = _pie_from_counts(gender_table, f"Gender{title_suffix}")

    # --- Ethnicity ---
    if "Q3" in df.columns:
        eth_raw = df["Q3"].apply(_to_int_safe)
        # exclude refused
        eth_raw = eth_raw.where(~eth_raw.isin([777]), other=np.nan)
        ethnicity = eth_raw.map(ETHNICITY_LABELS)
    else:
        ethnicity = pd.Series(dtype="object")
    ethnicity_table = _count_table(ethnicity, category_col="Category")
    ethnicity_fig = _pie_from_counts(ethnicity_table, f"Ethnicity{title_suffix}")

    # Ensure DataTable columns are strings (prevents your earlier error)
    for tdf in (age_table, gender_table, ethnicity_table):
        tdf.columns = [str(c) for c in tdf.columns]

    # --- UI layout (like your screenshot) ---
    return html.Div(
        [
            dbc.Card(
                dbc.CardBody(
                    [
                        dbc.Row(
                            [
                                dbc.Col(dcc.Graph(figure=age_fig, config={"displayModeBar": False}), md=4),
                                dbc.Col(dcc.Graph(figure=gender_fig, config={"displayModeBar": False}), md=4),
                                dbc.Col(dcc.Graph(figure=ethnicity_fig, config={"displayModeBar": False}), md=4),
                            ],
                            className="g-2",
                        ),

                        html.Hr(),

                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        html.H5("Age bins – Count table"),
                                        dash_table.DataTable(
                                            data=age_table.to_dict("records"),
                                            columns=[{"name": str(c), "id": str(c)} for c in age_table.columns],
                                            style_cell={"textAlign": "left", "padding": "8px"},
                                            style_header={"fontWeight": "bold"},
                                            style_table={"overflowX": "auto"},
                                        ),
                                    ],
                                    md=4,
                                ),
                                dbc.Col(
                                    [
                                        html.H5("Gender – Count table"),
                                        dash_table.DataTable(
                                            data=gender_table.to_dict("records"),
                                            columns=[{"name": str(c), "id": str(c)} for c in gender_table.columns],
                                            style_cell={"textAlign": "left", "padding": "8px"},
                                            style_header={"fontWeight": "bold"},
                                            style_table={"overflowX": "auto"},
                                        ),
                                    ],
                                    md=4,
                                ),
                                dbc.Col(
                                    [
                                        html.H5("Ethnicity – Count table"),
                                        dash_table.DataTable(
                                            data=ethnicity_table.to_dict("records"),
                                            columns=[{"name": str(c), "id": str(c)} for c in ethnicity_table.columns],
                                            style_cell={"textAlign": "left", "padding": "8px"},
                                            style_header={"fontWeight": "bold"},
                                            style_table={"overflowX": "auto"},
                                        ),
                                    ],
                                    md=4,
                                ),
                            ],
                            className="g-2",
                        ),
                    ]
                ),
                style={"borderRadius": "12px"},
            ),
        ]
    )

def section_card(title: str, body, subtitle: str | None = None, class_name="mb-3"):
    return dbc.Card(
        dbc.CardBody(
            [
                html.H4(title, style={"marginBottom": "6px"}),
                html.Div(subtitle, style={"fontSize": "13px", "opacity": 0.75, "marginBottom": "12px"})
                if subtitle else None,
                body,
            ]
        ),
        style={"borderRadius": "14px", "boxShadow": "0 2px 10px rgba(0,0,0,0.06)"},
        className=class_name,
    )

def nice_counts_table(df_counts: pd.DataFrame):
    # Ensure columns are strings (prevents DataTable errors)
    df_counts = df_counts.copy()
    df_counts.columns = [str(c) for c in df_counts.columns]

    return dash_table.DataTable(
        data=df_counts.to_dict("records"),
        columns=[{"name": str(c), "id": str(c)} for c in df_counts.columns],
        style_as_list_view=True,
        style_table={"overflowX": "auto"},
        style_cell={"padding": "10px", "fontSize": "14px", "border": "none"},
        style_header={"fontWeight": "700", "border": "none"},
        style_data={"border": "none"},
        style_data_conditional=[
            {"if": {"row_index": "odd"}, "backgroundColor": "rgba(0,0,0,0.03)"}
        ],
    )

def gi_count_card(fig, gi_label: str, gi_mask: pd.Series, total_n: int):
    gi_n = int(gi_mask.sum())
    df_counts = pd.DataFrame({"Group": [gi_label, "Others"], "Count": [gi_n, total_n - gi_n]})
    fig.update_layout(height=360, margin=dict(l=20, r=20, t=60, b=20))
    body = dbc.Row(
        [
            dbc.Col(
                dcc.Graph(
                    figure=fig,
                    config={"displayModeBar": False},
                    style={"height": "360px"},
                ),
                md=8,
            ),
            dbc.Col(
                [
                    html.H6("Counts", style={"marginTop": "4px"}),
                    nice_counts_table(df_counts),
                ],
                md=4,
            ),
        ],
        className="g-2",
    )
    return section_card(
        title=f"{gi_label} Count",
        body=body,
    )
# ============================================================

def gi_page_layout(
    df: pd.DataFrame,
    gi_label: str,
    gi_content_index: int,
    mapping_rows: list[dict],
    *,
    build_mapping_table_fn,
    gi_one_row_table_fn,
    gi_content_dict,
    gi_count_bar_from_unique_fn,
    demographics_section_like_card_fn,
    gi_utilisation_section_individual_unique_fn,
):
    # ---- reuse your existing unique assignment functions ----
    fig, gi_mask = gi_count_bar_from_unique_fn(df, gi_label)
    df_gi = df[gi_mask].copy()

    mapping_table = build_mapping_table_fn(mapping_rows, title=f"Global Impression – {gi_label}")
    mapping_card = section_card("Logic & Mapping", mapping_table)

    count_card = gi_count_card(fig, gi_label, gi_mask, total_n=len(df))
    demo_card = section_card("Demographics", demographics_section_like_card_fn(df_gi, title_suffix=""))
    util_card = section_card(
        "Healthcare Utilisation",
        gi_utilisation_section_individual_unique_fn(df, gi_label),    )

    return html.Div(
        [
            gi_one_row_table_fn(gi_content_dict[gi_content_index]),
            mapping_card,
            count_card,
            demo_card,
            util_card,
        ],
        style={"padding": "8px 6px"},
    )

# ============================================================
# GI × Demographics tables (Count + % within GI)
# ============================================================

def _format_count_pct(count: int, denom: int) -> str:
    if denom <= 0:
        return "0 (0.0%)"
    pct = (count / denom) * 100
    return f"{int(count)} ({pct:.1f}%)"


def gi_x_demographics_table(
    df: pd.DataFrame,
    *,
    value_series: pd.Series,
    categories: list[str],
    title_col: str,
    gi_col: str = "GI_Assigned",
) -> pd.DataFrame:
    """
    Generic GI × demographic table.
    Rows: GI I..GI V (and optionally Unclassified if you want)
    Cols: categories (e.g., age bins)
    Values: "Count (Pct%)" where % is within that GI row total (for this demographic, excluding NA).
    """
    dff = add_unique_gi_column(df, gi_col)

    tmp = pd.DataFrame({
        gi_col: dff[gi_col].astype(str),
        title_col: value_series.astype("object")
    }, index=dff.index)

    # Keep only the categories we care about (drop NA and unexpected)
    tmp = tmp[tmp[title_col].isin(categories)].copy()
    if tmp.empty:
        return pd.DataFrame()

    # Count by (GI, category)
    counts = (
        tmp.groupby([gi_col, title_col])
           .size()
           .reset_index(name="Count")
    )

    # Make full grid (GI rows x category cols)
    gi_rows = ["GI I", "GI II", "GI III", "GI IV", "GI V"]  # per your ask (no Unclassified)
    full_index = pd.MultiIndex.from_product([gi_rows, categories], names=[gi_col, title_col])

    counts = (
        counts.set_index([gi_col, title_col])
              .reindex(full_index, fill_value=0)
              .reset_index()
    )

    # Denominator per GI (only among the kept categories / non-missing)
    gi_denoms = counts.groupby(gi_col)["Count"].transform("sum")

    counts["Label"] = [
        _format_count_pct(c, d) for c, d in zip(counts["Count"], gi_denoms)
    ]

    table = (
        counts.pivot(index=gi_col, columns=title_col, values="Label")
              .reindex(gi_rows)
              .reset_index()
    )
    table.columns.name = None
    table = table.rename(columns={gi_col: "GI Category"})
    return table


def gi_age_by_gi_table(df: pd.DataFrame, gi_col: str = "GI_Assigned") -> pd.DataFrame:
    if "Q2" not in df.columns:
        return pd.DataFrame()
    age_bins = df["Q2"].apply(_age_bin_from_q2)
    age_bins = pd.Series(
        pd.Categorical(age_bins, categories=AGE_BIN_ORDER, ordered=True),
        index=df.index
    ).astype("object")
    return gi_x_demographics_table(
        df,
        value_series=age_bins,
        categories=AGE_BIN_ORDER,
        title_col="AgeBin",
        gi_col=gi_col
    )


def gi_gender_by_gi_table(df: pd.DataFrame, gi_col: str = "GI_Assigned") -> pd.DataFrame:
    if "Q4" not in df.columns:
        return pd.DataFrame()
    gender = df["Q4"].apply(_to_int_safe).map(GENDER_LABELS).astype("object")
    categories = ["Male", "Female"]
    return gi_x_demographics_table(
        df,
        value_series=gender,
        categories=categories,
        title_col="Gender",
        gi_col=gi_col
    )


def gi_ethnicity_by_gi_table(df: pd.DataFrame, gi_col: str = "GI_Assigned") -> pd.DataFrame:
    if "Q3" not in df.columns:
        return pd.DataFrame()
    eth_raw = df["Q3"].apply(_to_int_safe)
    eth_raw = eth_raw.where(~eth_raw.isin([777]), other=np.nan)  # drop refused
    ethnicity = eth_raw.map(ETHNICITY_LABELS).astype("object")
    categories = ["Chinese", "Malay", "Indian", "Other"]
    return gi_x_demographics_table(
        df,
        value_series=ethnicity,
        categories=categories,
        title_col="Ethnicity",
        gi_col=gi_col
    )


def gi_demographics_by_gi_section(df: pd.DataFrame):
    """
    Section for GI unique summary page:
      - 3 tables: Age by GI, Gender by GI, Ethnicity by GI
      - each cell = Count (Pct%) within that GI
    """
    age_tbl = gi_age_by_gi_table(df)
    gender_tbl = gi_gender_by_gi_table(df)
    eth_tbl = gi_ethnicity_by_gi_table(df)

    blocks = []

    def _dt(title, tdf):
        if tdf is None or tdf.empty:
            return html.Div([html.H4(title), html.P("No data available.")])

        # make sure column ids are strings for DataTable
        tdf = tdf.copy()
        tdf.columns = [str(c) for c in tdf.columns]

        return html.Div(
            [
                html.H4(title),
                dash_table.DataTable(
                    data=tdf.to_dict("records"),
                    columns=[{"name": str(c), "id": str(c)} for c in tdf.columns],
                    style_cell={"textAlign": "center", "padding": "8px"},
                    style_header={"fontWeight": "bold"},
                    style_table={"overflowX": "auto"},
                ),
                html.Br(),
            ]
        )

    blocks.append(_dt("Age × GI", age_tbl))
    blocks.append(_dt("Gender × GI", gender_tbl))
    blocks.append(_dt("Ethnicity × GI", eth_tbl))

    return html.Div(blocks)


# ============================================================
# Simple GI count layouts
# ============================================================
def GI_I_layout(df: pd.DataFrame):
    mapping_rows = [
    {
        "Global Impression": "Global Impression – I (Healthy)",
        "Mapped Question No from Survey": "Q124, Q126, Q128, Q129, Q130",
        "Question Description": (
            "Q124. Have you been told by a western-trained doctor that you have high blood pressure?\n"
            "1) Yes\n"
            "2) No\n"
            "3) No, but I have borderline hypertension\n"
            "777) Refused\n"
            "888) Do not know\n\n"
            "Q126. Have you ever been told by a western-trained doctor that you have diabetes?\n"
            "1) Yes\n"
            "2) No\n"
            "3) No, but I have pre-diabetes or borderline diabetes\n"
            "777) Refused\n"
            "888) Do not know\n\n"
            "Q128. Have you been told by a western-trained doctor that you have high blood cholesterol or lipids?\n"
            "1) Yes\n"
            "2) No\n"
            "3) No, but I have borderline high blood cholesterol\n"
            "777) Refused\n"
            "888) Do not know\n\n"
            "Q129. Has the resident been told by a western-trained doctor that he/she have Dementia/Alzheimer’s?\n"
            "1) Yes\n"
            "2) No\n"
            "777) Refused\n"
            "888) Do not know\n\n"
            "Q130. Have you ever been told by a western-trained doctor that you have other chronic conditions apart from those mentioned?\n"
            "1) Yes, please specify:\n"
            "2) No\n"
        ),
        "GI Definition": "Healthy",
        "Data Mapping": (
            "Q124 –\n"
            "1) Yes\n"
            "2) No\n"
            "3) No, but I have borderline hypertension\n"
            "777) X\n"
            "888) Do not know\n\n"
            "Q126 –\n"
            "1) Yes\n"
            "2) No\n"
            "3) No, but I have pre-diabetes or borderline diabetes\n"
            "777) X\n"
            "888) Do not know\n\n"
            "Q128 –\n"
            "1) Yes\n"
            "2) No\n"
            "3) No, but I have borderline high blood cholesterol\n"
            "777) X\n"
            "888) Do not know\n\n"
            "Q129 –\n"
            "1) Yes\n"
            "2) No\n"
            "777) X\n"
            "888) Do not know\n\n"
            "Q130 –\n"
            "1) Yes\n"
            "2) No\n"
        ),
        "Coding": (
            "If (Q124 == 2 AND Q126 == 2 AND Q128 == 2 AND "
            "Q129 == 2 AND Q130 == 2)\n"
            "AND if GI_IV == 0 -> GI I (Healthy)"
        ),
        }
    ]

    return gi_page_layout(
        df=df,
        gi_label="GI I",
        gi_content_index=1,
        mapping_rows=mapping_rows,
        build_mapping_table_fn=build_mapping_table,
        gi_one_row_table_fn=gi_one_row_table,
        gi_content_dict=GI_CONTENT,
        gi_count_bar_from_unique_fn=gi_count_bar_from_unique,
        demographics_section_like_card_fn=demographics_section_like_card,
        gi_utilisation_section_individual_unique_fn=gi_utilisation_section_individual_unique,
    )


def GI_II_layout(df: pd.DataFrame):
    mapping_rows = [
    {
        "Global Impression": "Global Impression – II",
        "Mapped Question No from Survey": "Q124\nQ130\nQ142",
        "Question Description": (
            "Q124. Have you been told by a western-trained doctor that you have high blood pressure?\n"
            "1) Yes\n"
            "2) No\n"
            "3) No, but I have borderline hypertension\n"
            "777) Refused\n"
            "888) Do not know\n\n"
            "Q130 –\n"
            "Have you ever been told by a western-trained doctor that you have other chronic conditions apart from those mentioned?\n"
            "1) Yes, please specify:\n\n"
            "non-life-threatening conditions:\n"
            "G)	Digestive illness (stomach or intestinal)\n"
            "J)	Joint pain, arthritis, rheumatism or nerve pain\n"
            "K)	Chronic back pain\n"
            "L)	Osteoporosis\n"
            "O)	Cataract\n"
            "P)	Glaucoma\n"
            "Q)	Age-related macular degeneration\n"
            "S)	Chronic skin condition (e.g. eczema, psoriasis)\n"
            "T)	Epilepsy\n"
            "U)	Thyroid disorder\n"
            "V)	Migraine\n"
            "W)	Parkinsonism\n"
            "2) No\n\n"
            "Q142 –\n"
            "For the past 6 months or more, have you been limited in activities people usually do because of a health problem?\n"
            "1) Yes, strongly limited\n"
            "2) Yes, limited\n"
            "3) No, not limited\n"
            "777) Refused\n"
            "888) Do not know\n"
        ),
        "GI Definition": "Chronic conditions, asymptomatic",
        "Data Mapping": (
            "Q124 –\n"
            "1) Yes\n"
            "2) No\n"
            "3) No, but I have borderline hypertension\n"
            "777) X\n"
            "888) Do not know\n\n"
            "Q130 –\n"
            "1) Yes\n"
            "2) No\n\n"
            "Q142 –\n"
            "1) Yes, strongly limited\n"
            "2) Yes, limited\n"
            "3) No, not limited\n"
            "777) Refused\n"
            "888) Do not know\n"
        ),
        "Coding": (
            "[(Any Q130 non-life threatening condition >= 1)\n"
            "OR (Q124 == 1 OR Q124 == 3)]\n"
            "OR (Q142 == 3) -> GI II (Chronic conditions, asymptomatic)"
        ),

        }
    ]
    return gi_page_layout(
        df=df,
        gi_label="GI II",
        gi_content_index=2,
        mapping_rows=mapping_rows,
        build_mapping_table_fn=build_mapping_table,
        gi_one_row_table_fn=gi_one_row_table,
        gi_content_dict=GI_CONTENT,
        gi_count_bar_from_unique_fn=gi_count_bar_from_unique,
        demographics_section_like_card_fn=demographics_section_like_card,
        gi_utilisation_section_individual_unique_fn=gi_utilisation_section_individual_unique,
    )

def GI_III_layout(df: pd.DataFrame):
    mapping_rows = [
    {
        "Global Impression": "Global Impression – III",
        "Mapped Question No from Survey": "Q124\nQ130\nQ142",
        "Question Description": (
            "Q124. Have you been told by a western-trained doctor that you have high blood pressure?\n"
            "1) Yes\n"
            "2) No\n"
            "3) No, but I have borderline hypertension\n"
            "777) Refused\n"
            "888) Do not know\n\n"
            "Q130 –\n"
            "Have you ever been told by a western-trained doctor that you have other chronic conditions apart from those mentioned?\n"
            "1) Yes, please specify:\n\n"
            "life-threatening conditions:\n"
            "A)	Heart attack (myocardial infarction), angina\n"
            "B)	Heart failure\n"
            "C)	Other forms of heart diseases\n"
            "D)	Cancer\n"
            "E)	Cerebrovascular diseases (such as stroke)\n"
            "F)	Chronic respiratory illness (e.g. asthma or COPD [chronic obstructive pulmonary disease])\n"
            "H)	Renal / kidney or urinary tract ailments\n"
            "I)	Ailments of the liver or gall bladder\n"
            "M)	Fractures of the hip, thigh and pelvis\n\n"
            "non-life-threatening conditions:\n"
            "G)	Digestive illness (stomach or intestinal)\n"
            "J)	Joint pain, arthritis, rheumatism or nerve pain\n"
            "K)	Chronic back pain\n"
            "L)	Osteoporosis\n"
            "O)	Cataract\n"
            "P)	Glaucoma\n"
            "Q)	Age-related macular degeneration\n"
            "S)	Chronic skin condition (e.g. eczema, psoriasis)\n"
            "T)	Epilepsy\n"
            "U)	Thyroid disorder\n"
            "V)	Migraine\n"
            "W)	Parkinsonism\n"
            "\n"
            "2) No\n\n"
            "Q142 –\n"
            "For the past 6 months or more, have you been limited in activities people usually do because of a health problem?\n"
            "1) Yes, strongly limited\n"
            "2) Yes, limited\n"
            "3) No, not limited\n"
            "777) Refused\n"
            "888) Do not know\n"
        ),
        "GI Definition": "Chronic conditions, stable but moderately/seriously symptomatic or silently severe",
        "Data Mapping": (
            "Q124 –\n"
            "1) Yes\n"
            "2) No\n"
            "3) No, but I have borderline hypertension\n"
            "777) X\n"
            "888) Do not know\n\n"
            "Q130 –\n"
            "1) Yes\n"
            "2) No\n\n"
            "Q142 –\n"
            "1) Yes, strongly limited\n"
            "2) Yes, limited\n"
            "3) No, not limited\n"
            "777) Refused\n"
            "888) Do not know\n"
        ),
        "Coding": "(At least one of Q130_G, Q130_J, Q130_K, Q130_L,\n"
            "Q130_O, Q130_P, Q130_Q,\n"
            "Q130_S, Q130_T, Q130_U, Q130_V, Q130_W = 1\n"
            "OR (Q124 == 1 OR Q124 == 3)]\n"
            "AND\n"
            "[Q142 == 1]\n\n"
            "OR\n\n"
            "[At least one of Q130_A, Q130_B, Q130_C, Q130_D,\n"
            "Q130_E, Q130_F, Q130_H, Q130_I, Q130_M = 1]\n"
            "AND\n"
            "[Q142 == 3]\n"
            "-> GI III (Chronic conditions, stable but moderately/seriously symptomatic "
            "or silently severe)",
        }
    ]
    return gi_page_layout(
        df=df,
        gi_label="GI III",
        gi_content_index=3,
        mapping_rows=mapping_rows,
        build_mapping_table_fn=build_mapping_table,
        gi_one_row_table_fn=gi_one_row_table,
        gi_content_dict=GI_CONTENT,
        gi_count_bar_from_unique_fn=gi_count_bar_from_unique,
        demographics_section_like_card_fn=demographics_section_like_card,
        gi_utilisation_section_individual_unique_fn=gi_utilisation_section_individual_unique,
    )

def GI_IV_layout(df: pd.DataFrame):
    mapping_rows = [
    {
        "Global Impression": "Global Impression – IV",
        "Mapped Question No from Survey": (
            "Q129,\n"
            "Q142,\n"
            "Q16 – Q26"
        ),
        "Question Description": (
            "S0 : Responded by - Participant / Proxy\n\n"
            "Q129 –\n"
            "Has the resident been told by a western-trained doctor that he/she have Dementia/ Alzheimer’s?\n"
            "1) Yes\n"
            "2) No\n"
            "777) Refused\n"
            "888) Do not know\n\n"
            "Q142 –\n"
            "For the past 6 months or more, have you been limited in activities people usually do because of a health problem?\n"
            "1) Yes, strongly limited\n"
            "2) Yes, limited\n"
            "3) No, not limited\n"
            "777) Refused\n"
            "888) Do not know\n\n"
            "Interviewer: I am going to ask you a few questions to test your memory.\n\n"
            "16. What is the month?\n"
            "17. What is the year?\n"
            "18. What is the time? (within 1 hour)\n"
            "19. What is your age?\n"
            "20. What is your date of birth?\n"
            "21. What is your home address?\n"
            "22. Where are we now?\n"
            "23. Who is our country’s Prime Minister?\n"
            "24. Recognition of 2 persons (use showcards in Annex A)\n"
            "What is his/her job?\n"
            "25. Count backwards from 20 to 1\n"
            "26. Please recall the memory phrase\n"
        ),
        "GI Definition": "Long course of decline",
        "Data Mapping": (
            "S0-\n"
            "1) Participant\n"
            "2) Proxy\n\n"
            "Q129 –\n"
            "1) Yes\n"
            "2) No\n"
            "777) X (Refused)\n"
            "888) Do not know\n\n"
            "Q142 –\n"
            "1) Yes, strongly limited\n"
            "2) Yes, limited\n"
            "3) No, not limited\n"
            "777) Refused\n"
            "888) Do not know\n\n"
            "Q16 – Q26 –\n"
            "1) Pass (mapped to 1)\n"
            "2) Fail (mapped to 0)\n"
            "777) X (Refused)\n"
            "999) Not applicable\n"
        ),
        "Coding": (
            "At least 2 of the following:\n"
            "1) If S0 == 2 AND Q129 == 1\n"
            "2) If Q142 <= 2\n"
            "3) If sum Q16 – Q26 < 5\n"
        ),
    }
]
    return gi_page_layout(
        df=df,
        gi_label="GI IV",
        gi_content_index=4,
        mapping_rows=mapping_rows,
        build_mapping_table_fn=build_mapping_table,
        gi_one_row_table_fn=gi_one_row_table,
        gi_content_dict=GI_CONTENT,
        gi_count_bar_from_unique_fn=gi_count_bar_from_unique,
        demographics_section_like_card_fn=demographics_section_like_card,
        gi_utilisation_section_individual_unique_fn=gi_utilisation_section_individual_unique)

def GI_V_layout(df: pd.DataFrame):
    mapping_rows = [
    {
        "Global Impression": "Global Impression – V",
        "Mapped Question No from Survey": (
            "Q96\n"
            "Q103\n"
            "Q130"
        ),
        "Question Description": (
            "Q96 –\n"
            "In the past 12 months, how many times have you had public hospital admissions including public community hospital admissions\n"
            "1) 0\n"
            "2) No.of times (exclude 0):\n"
            "666) Unable to recall\n"
            "777) Refused\n"
            "Q103 –\n"
            "In the past 12 months, how many times have you had private hospital admissions\n"
            "1) 0\n"
            "2) No.of times (exclude 0):\n"
            "3) No, not limited\n"
            "666) Unable to recall\n"
            "777) Refused\n\n"
            "Q130 –\n"
            "Have you ever been told by a western-trained doctor that you have other chronic conditions apart from those mentioned?\n"
            "1) Yes, please specify:\n\n"
            "non-life-threatening conditions:\n"
            "G)	Digestive illness (stomach or intestinal)\n"
            "J)	Joint pain, arthritis, rheumatism or nerve pain\n"
            "K)	Chronic back pain\n"
            "L)	Osteoporosis\n"
            "O)	Cataract\n"
            "P)	Glaucoma\n"
            "Q)	Age-related macular degeneration\n"
            "S)	Chronic skin condition (e.g. eczema, psoriasis)\n"
            "T)	Epilepsy\n"
            "U)	Thyroid disorder\n"
            "V)	Migraine\n"
            "W)	Parkinsonism\n"
            "\n"
            "2) No\n\n"
           
        ),
        "GI Definition": "Limited reserve & serious exacerbations",
        "Data Mapping": (
            "Q96 –\n"
            "666) Unable to recall\n"
            "777) X (Refused)\n"
            "Q103 –\n"
            "666) Unable to recall\n"
            "777) X (Refused)\n"
            "Q130 –\n"
            "1) Yes\n"
            "2) No\n\n"
        ),
        "Coding": (
            "If Q96 >= 2 OR Q103 == 1 AND Q130 >= 2\n"
            "& At least one of Q130_A, Q130_B, Q130_C, Q130_D,\n"
            "Q130_E, Q130_F, Q130_H, Q130_I, Q130_M = 1]\n"
            "-> GI V (Limited reserve & serious exacerbations)"
        ),
    }
]
    return gi_page_layout(
        df=df,
        gi_label="GI V",
        gi_content_index=5,
        mapping_rows=mapping_rows,
        build_mapping_table_fn=build_mapping_table,
        gi_one_row_table_fn=gi_one_row_table,
        gi_content_dict=GI_CONTENT,
        gi_count_bar_from_unique_fn=gi_count_bar_from_unique,
        demographics_section_like_card_fn=demographics_section_like_card,
        gi_utilisation_section_individual_unique_fn=gi_utilisation_section_individual_unique,
    )