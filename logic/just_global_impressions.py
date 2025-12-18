import pandas as pd
from dash import html, dcc
import plotly.express as px
from logic.mapping_helpers import build_mapping_table
from logic.gi_table_helper import gi_one_row_table
from logic.gi_content import GI_CONTENT

# ============================================================
# Constants
# ============================================================
GI_IV_S0_COL = "S0"
GI_IV_Q129_COL = "Q129"
GI_IV_Q142_COL = "Q142"
GI_IV_COG_COLS = [f"Q{i}" for i in range(16, 27)]  # Q16 ... Q26
UTIL_QS = ["Q78", "Q85", "Q91", "Q93", "Q96", "Q103"]
UTIL_BIN_ORDER = ["0"] + [str(i) for i in range(1, 11)] + ["11+"]
GI_II_NLT_COLS = ["Q130_G", "Q130_J", "Q130_K", "Q130_L", "Q130_O", "Q130_P", "Q130_Q", "Q130_S", "Q130_T", "Q130_U", "Q130_V", "Q130_W"]
GI_III_LT_COLS = ["Q130_A", "Q130_B", "Q130_C", "Q130_D","Q130_E", "Q130_F", "Q130_H", "Q130_I", "Q130_M"]

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
        # Treat special codes as 0 (not meeting ">=2")
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
GI_ORDER_SEVERE_TO_MILD = ["GI V", "GI IV", "GI III", "GI II", "GI I"]

def compute_unique_gi_labels(df: pd.DataFrame) -> pd.Series:
    """
    Returns ONE GI label per row by severity:
      GI V > GI IV > GI III > GI II > GI I > Unclassified

    This resolves overlaps by removing already-assigned rows at each step.
    """
    idx = df.index
    out = pd.Series("Unclassified", index=idx, dtype="object")

    # Compute raw masks (can overlap)
    m5 = df.apply(gi_v_flag, axis=1).fillna(False)
    m4 = df.apply(gi_iv_flag, axis=1).fillna(False)
    m3 = df.apply(gi_iii_flag, axis=1).fillna(False)
    m2 = df.apply(gi_ii_flag, axis=1).fillna(False)

    # GI I mask should be computed independently (don’t rely on gi_i_flag because it only excludes GI IV)
    healthy = (
        (df["Q124"] == 2) &
        (df["Q126"] == 2) &
        (df["Q128"] == 2) &
        (df["Q129"] == 2) &
        (df["Q130"] == 2)
    ).fillna(False)

    m1 = healthy & (~m4)  # keep your original GI I rule: healthy AND not GI IV

    # Resolve overlaps by severity (highest wins)
    out.loc[m5] = "GI V"
    out.loc[m4 & ~m5] = "GI IV"
    out.loc[m3 & ~(m4 | m5)] = "GI III"
    out.loc[m2 & ~(m3 | m4 | m5)] = "GI II"
    out.loc[m1 & ~(m2 | m3 | m4 | m5)] = "GI I"

    return out

# ============================================================
# Stepwiswe escalation helpers
# ============================================================

def compute_stepwise_escalation_labels(df: pd.DataFrame):
    """
    Stepwise escalation (mild -> severe):
      Start at GI I (only those who meet GI I),
      then compare with GI II: promote overlaps to GI II,
      then compare with GI III: promote overlaps to GI III,
      then GI IV, then GI V.

    Returns:
      labels: pd.Series of final labels (1 per respondent)
      summary: pd.DataFrame describing step-by-step upgrades
    """
    idx = df.index
    labels = pd.Series("Unclassified", index=idx, dtype="object")

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

    # Keep your original GI I rule: healthy AND not GI IV
    m1 = healthy & (~m4)

    # ---- Step 0: seed with GI I only ----
    labels.loc[m1] = "GI I"

    steps = []

    def _step_promote(from_labels, to_label, to_mask):
        """Promote only overlaps: those already in from_labels AND satisfy to_mask."""
        promotable = labels.isin(from_labels) & to_mask
        n_before = int((labels == to_label).sum())  # usually 0
        n_promoted = int(promotable.sum())
        labels.loc[promotable] = to_label
        n_after = int((labels == to_label).sum())

        steps.append({
            "Step": f"{'/'.join(from_labels)} → {to_label}",
            "Eligible in previous bucket": int(labels.isin(from_labels + [to_label]).sum()),
            "Promoted this step": n_promoted,
            "Total now in target": n_after
        })

    # GI I vs GI II: overlaps become GI II
    _step_promote(["GI I"], "GI II", m2)

    # (GI I or GI II) vs GI III: overlaps become GI III
    _step_promote(["GI I", "GI II"], "GI III", m3)

    # (GI I/II/III) vs GI IV: overlaps become GI IV
    _step_promote(["GI I", "GI II", "GI III"], "GI IV", m4)

    # (GI I/II/III/IV) vs GI V: overlaps become GI V
    _step_promote(["GI I", "GI II", "GI III", "GI IV"], "GI V", m5)

    summary = pd.DataFrame(steps)
    return labels, summary

# ============================================================
# Stepwise escalation chart helpers
# ============================================================
def gi_stepwise_escalation_chart(df: pd.DataFrame):
    labels, summary = compute_stepwise_escalation_labels(df)

    # Bar chart: promotions per step
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
        title="Unique GI Distribution (Highest severity wins; 1 GI per respondent)",
        category_orders={"GI": order},
    )
    counts["Pct"] = counts["Count"] / counts["Count"].sum() * 100
    fig.update_traces(text=[f"{c} ({p:.1f}%)" for c, p in zip(counts["Count"], counts["Pct"])], textposition="outside")

    fig.update_layout(
        xaxis_title="GI Category",
        yaxis_title="Number of respondents",
        margin=dict(l=30, r=30, t=70, b=40),
        height=450,
        yaxis_type="log"
    )
    return fig

# ============================================================
# Utilisation chart helpers (GENERIC)
# ============================================================
def bin_util_value(v):
    """
    Bucket utilisation values to: 0, 1..10, 11+.
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
    if 1 <= iv <= 10:
        return str(iv)
    return "11+"


# ============================================================
# GI I – Healthy
# ============================================================
def GI_I_layout(df: pd.DataFrame):
    healthy_mask = ( (df["Q124"] == 2) & (df["Q126"] == 2) & (df["Q128"] == 2) & (df["Q129"] == 2) & (df["Q130"] == 2) ) 
    gi4_mask = df.apply(gi_iv_flag, axis=1) 
    gi1_mask = healthy_mask & (~gi4_mask)
    gi1_count = int(gi1_mask.sum())
    total = int(len(df))
    count_table = pd.DataFrame({"Group": ["GI I", "Others"], "Count": [gi1_count, total - gi1_count]})
    fig = px.bar(count_table, x="Group", y="Count", title="GI I – Count of Respondents Meeting GI I Logic", text="Count")

    return html.Div([
        dcc.Graph(figure=fig, config={"displayModeBar": False}),
        html.Br(),
    ])

# ============================================================
# GI II – Chronic conditions, asymptomatic-ish
# ============================================================
def GI_II_layout(df: pd.DataFrame):
    gi2_mask = df.apply(lambda r: gi_ii_flag(r), axis=1)
    gi2_count = int(gi2_mask.sum())
    total = int(len(df))
    count_table = pd.DataFrame({"Group": ["GI II", "Others"], "Count": [gi2_count, total - gi2_count]})
    fig = px.bar(count_table, x="Group", y="Count", title="GI II – Count of Respondents Meeting GI II Logic", text="Count")
    return html.Div([
        dcc.Graph(figure=fig, config={"displayModeBar": False}),
        html.Br(),
    ])

# ============================================================
# GI III – Chronic conditions, stable but moderately/symptomatic
# ============================================================
def GI_III_layout(df: pd.DataFrame):
    gi3_mask = df.apply(lambda r: gi_iii_flag(r), axis=1)
    gi3_count = int(gi3_mask.sum())
    total = int(len(df))
    count_table = pd.DataFrame({"Group": ["GI III", "Others"], "Count": [gi3_count, total - gi3_count]})
    fig = px.bar(count_table, x="Group", y="Count", title="GI III – Count of Respondents Meeting GI III Logic", text="Count")
    return html.Div([
        dcc.Graph(figure=fig, config={"displayModeBar": False}),
        html.Br(),
    ])

# ============================================================
# GI IV – Long course of decline
# ============================================================
def GI_IV_layout(df: pd.DataFrame):
    gi4_mask = df.apply(gi_iv_flag, axis=1)
    gi4_count = int(gi4_mask.sum())
    total = int(len(df))
    count_table = pd.DataFrame({"Group": ["GI IV", "Others"], "Count": [gi4_count, total - gi4_count]})
    fig = px.bar(count_table, x="Group", y="Count", title="GI IV – Count of Respondents Meeting GI IV Logic", text="Count")
    return html.Div([
        dcc.Graph(figure=fig, config={"displayModeBar": False}),
    ])

# ============================================================
# GI V – Limited reserve & serious exacerbations
# ============================================================
def GI_V_layout(df: pd.DataFrame):
    gi5_mask = df.apply(gi_v_flag, axis=1)
    gi5_count = int(gi5_mask.sum())
    total = int(len(df))
    count_table = pd.DataFrame({"Group": ["GI V", "Others"], "Count": [gi5_count, total - gi5_count]})
    fig = px.bar(count_table, x="Group", y="Count", title="GI V – Count of Respondents Meeting GI V Logic", text="Count")
    return html.Div([
        dcc.Graph(figure=fig, config={"displayModeBar": False}),
    ])