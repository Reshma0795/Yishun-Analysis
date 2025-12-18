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
GI_ASSIGN_ORDER = ["GI I", "GI II", "GI III", "GI IV", "GI V", "Unclassified"]

def assign_gi_label(row) -> str:
    # priority: most severe first (note: GI V placement depends on your rulebook)
    if gi_v_flag(row):
        return "GI V"
    if gi_iv_flag(row):
        return "GI IV"
    if gi_iii_flag(row):
        return "GI III"
    if gi_ii_flag(row):
        return "GI II"
    if gi_i_flag(row):
        return "GI I"
    return "Unclassified"

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


def util_counts_long_for_gi(df: pd.DataFrame, gi_mask: pd.Series, util_q: str) -> pd.DataFrame:
    """
    Returns long-form counts by utilisation bin and GI membership:
      columns: [util_q, Group, Count]
      Group in {"In GI", "Not in GI"}
    """
    if util_q not in df.columns:
        return pd.DataFrame()

    tmp = df[[util_q]].copy()
    tmp["UtilBin"] = tmp[util_q].apply(bin_util_value)
    tmp = tmp[tmp["UtilBin"].notna()].copy()

    mask_aligned = gi_mask.reindex(tmp.index).fillna(False)

    tmp["Group"] = mask_aligned.map({True: "In GI", False: "Not in GI"})

    out = (
        tmp.groupby(["UtilBin", "Group"])
           .size()
           .reset_index(name="Count")
    )

    # Ensure all bins exist for consistent axis
    all_bins = pd.DataFrame({"UtilBin": UTIL_BIN_ORDER})
    out = all_bins.merge(out, on="UtilBin", how="left").fillna({"Group": "In GI", "Count": 0})
    # The merge above can duplicate incorrectly; better ensure bins with both groups:
    out = (
        tmp.assign(UtilBin=pd.Categorical(tmp["UtilBin"], categories=UTIL_BIN_ORDER, ordered=True))
           .groupby(["UtilBin", "Group"])
           .size()
           .reset_index(name="Count")
    )
    # add missing combinations
    full_index = pd.MultiIndex.from_product([UTIL_BIN_ORDER, ["In GI", "Not in GI"]], names=["UtilBin", "Group"])
    out = out.set_index(["UtilBin", "Group"]).reindex(full_index, fill_value=0).reset_index()

    out = out.rename(columns={"UtilBin": util_q})
    out[util_q] = pd.Categorical(out[util_q], categories=UTIL_BIN_ORDER, ordered=True)
    return out


def util_chart_for_gi(df: pd.DataFrame, gi_mask: pd.Series, util_q: str, gi_title: str):
    """
    Grouped bar chart: utilisation bin on x, counts on y, bars = In GI vs Not in GI.
    """
    data_long = util_counts_long_for_gi(df, gi_mask, util_q)
    if data_long.empty:
        return None

    fig = px.bar(
        data_long,
        x=util_q,
        y="Count",
        color="Group",
        barmode="group",
        text="Count",
        title=f"{gi_title} vs {util_q} (Counts by utilisation bucket)",
        category_orders={util_q: UTIL_BIN_ORDER, "Group": ["In GI", "Not in GI"]},
    )

    fig.update_traces(textposition="outside", cliponaxis=False)

    fig.update_layout(
        xaxis_title=f"{util_q} (bucketed: 0, 1–10, 11+)",
        yaxis_title="Number of respondents",
        legend_title="Group",
        margin=dict(l=30, r=30, t=60, b=40),
        height=420,
    )

    return fig


def utilisation_charts_section_for_gi(df: pd.DataFrame, gi_mask: pd.Series, gi_title: str):
    charts = []
    for q in UTIL_QS:
        if q in df.columns:
            fig = util_chart_for_gi(df, gi_mask, q, gi_title)
            if fig is not None:
                charts.append(
                    html.Div(
                        dcc.Graph(figure=fig, config={"displayModeBar": False}),
                        style={"marginBottom": "18px"}
                    )
                )

    return html.Div([
        html.H4("Healthcare Utilisation (Counts)", style={"marginTop": "26px"}),
        html.Div(charts),
    ])


# ============================================================
# GI I – Healthy
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

    mapping_table = build_mapping_table(mapping_rows, title="Global Impression – GI I (Healthy)")
    healthy_mask = ( (df["Q124"] == 2) & (df["Q126"] == 2) & (df["Q128"] == 2) & (df["Q129"] == 2) & (df["Q130"] == 2) ) 
    gi4_mask = df.apply(gi_iv_flag, axis=1) 
    gi1_mask = healthy_mask & (~gi4_mask)
    gi1_count = int(gi1_mask.sum())
    total = int(len(df))
    count_table = pd.DataFrame({"Group": ["GI I", "Others"], "Count": [gi1_count, total - gi1_count]})

    fig = px.bar(count_table, x="Group", y="Count",
                 title="GI I – Count of Respondents Meeting GI I Logic", text="Count")

    util_section = utilisation_charts_section_for_gi(df, gi1_mask, "GI I")

    return html.Div([
        gi_one_row_table(GI_CONTENT[1]),
        mapping_table,
        html.Br(),
        dcc.Graph(figure=fig, config={"displayModeBar": False}),
        html.Br(),
        util_section,
        html.Br(),
    ])

# ============================================================
# GI II – Chronic conditions, asymptomatic-ish
# ============================================================
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

    mapping_table = build_mapping_table(mapping_rows, title="Global Impression – GI II")
    gi2_mask = df.apply(lambda r: gi_ii_flag(r), axis=1)
    gi2_count = int(gi2_mask.sum())
    total = int(len(df))
    count_table = pd.DataFrame({"Group": ["GI II", "Others"], "Count": [gi2_count, total - gi2_count]})
    fig = px.bar(count_table, x="Group", y="Count", title="GI II – Count of Respondents Meeting GI II Logic", text="Count")
    util_section = utilisation_charts_section_for_gi(df, gi2_mask, "GI II")
    return html.Div([
        gi_one_row_table(GI_CONTENT[2]),
        html.Br(),
        mapping_table,
        html.Br(),
        dcc.Graph(figure=fig, config={"displayModeBar": False}),
        html.Br(),
        util_section,
        html.Br(),
    ])


# ============================================================
# GI III – Chronic conditions, stable but moderately/symptomatic
# ============================================================
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

    mapping_table = build_mapping_table(mapping_rows, title="Global Impression – GI III")
    gi3_mask = df.apply(lambda r: gi_iii_flag(r), axis=1)
    gi3_count = int(gi3_mask.sum())
    total = int(len(df))
    count_table = pd.DataFrame({"Group": ["GI III", "Others"], "Count": [gi3_count, total - gi3_count]})
    fig = px.bar(count_table, x="Group", y="Count", title="GI III – Count of Respondents Meeting GI III Logic", text="Count")
    util_section = utilisation_charts_section_for_gi(df, gi3_mask, "GI III")
    return html.Div([
        gi_one_row_table(GI_CONTENT[3]),
        html.Br(),
        mapping_table,
        html.Br(),
        dcc.Graph(figure=fig, config={"displayModeBar": False}),
        html.Br(),
        util_section,
        html.Br(),
    ])


# ============================================================
# GI IV – Long course of decline
# ============================================================
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

    mapping_table = build_mapping_table(mapping_rows, title="GI IV - Long course of decline")
    gi4_mask = df.apply(gi_iv_flag, axis=1)
    gi4_count = int(gi4_mask.sum())
    total = int(len(df))
    count_table = pd.DataFrame({"Group": ["GI IV", "Others"], "Count": [gi4_count, total - gi4_count]})
    fig = px.bar(count_table, x="Group", y="Count", title="GI IV – Count of Respondents Meeting GI IV Logic", text="Count")
    util_section = utilisation_charts_section_for_gi(df, gi4_mask, "GI IV")
    return html.Div([
        gi_one_row_table(GI_CONTENT[4]),
        html.Br(),
        mapping_table,
        html.Br(),
        dcc.Graph(figure=fig, config={"displayModeBar": False}),
        html.Br(),
        util_section,
        html.Br(),
    ])


# ============================================================
# GI V – placeholder until you implement GI V logic
# ============================================================
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
    
    mapping_table = build_mapping_table(mapping_rows, title="GI V - Limited reserve & serious exacerbations")
    gi5_mask = df.apply(gi_v_flag, axis=1)
    gi5_count = int(gi5_mask.sum())
    total = int(len(df))
    count_table = pd.DataFrame({"Group": ["GI V", "Others"], "Count": [gi5_count, total - gi5_count]})
    fig = px.bar(count_table, x="Group", y="Count", title="GI V – Count of Respondents Meeting GI V Logic", text="Count")
    util_section = utilisation_charts_section_for_gi(df, gi5_mask, "GI V")
    return html.Div([
        gi_one_row_table(GI_CONTENT[5]),
        html.Br(),
        mapping_table,
        html.Br(),
        dcc.Graph(figure=fig, config={"displayModeBar": False}),
        html.Br(),
        util_section,
        html.Br(),
    ])