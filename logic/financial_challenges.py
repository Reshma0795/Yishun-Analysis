import pandas as pd
from dash import html, dcc, dash_table
import plotly.express as px
import dash_bootstrap_components as dbc
from logic.question_texts import HEALTHCARE_UTILIZATION_QUESTIONS
from logic.mapping_helpers import build_mapping_table
from logic.financial_value_counts_helpers import build_mapped_value_counts_table
from logic.demographics_helpers import add_age_bins, add_categorical_labels
from logic.cf_distribution_helpers import build_cf_value_column, cf_distribution_group_cf_on_y
from logic.utilization import build_cf_x_utilization_binned_tables_per_question
from logic.utilization_helpers import build_gp_visits, add_visit_bins, gp_visits_by_cf_group
from logic.cf_matrix_tables import build_cf_matrix_pct_n_table
from logic.ui_helpers import chart_card
# ------------------------------------------------------------
# J. Financial Challenges (Q108, Q109, Q110, Q111, Q74)
# ------------------------------------------------------------
Q108_COL = "Q108"
Q109_COL = "Q109"
Q110_COL = "Q110"
Q111_COL = "Q111"
Q74_COL  = "Q74"

HC_UTIL_QUESTIONS = ["Q78", "Q85", "Q91", "Q93", "Q96", "Q103"]

Q108_MAP = {
    1: "Yes",
    2: "No",
    3: "Not applicable (no need for healthcare)",
    4: "Refused / X",
}
Q110_MAP = Q108_MAP.copy()

Q109_MAP = {1: "Could not afford to (too expensive)"}
Q111_MAP = Q109_MAP.copy()

Q74_MAP = {
    1: "Strongly disagree",
    2: "Disagree",
    3: "Neither",
    4: "Agree",
    5: "Strongly agree",
    777: "Refused / X",
}

Q108_ORDER = [1, 2, 3, 4]
Q109_ORDER = [1]
Q110_ORDER = [1, 2, 3, 4]
Q111_ORDER = [1]
Q74_ORDER  = [1, 2, 3, 4, 5, 777]


def _to_int(x):
    if pd.isna(x):
        return None
    try:
        return int(x)
    except (TypeError, ValueError):
        return None

# -------------------------------
# Imputation helper (ONLY Q110)
# -------------------------------
def impute_q110_to_no(df: pd.DataFrame, col: str = "Q110") -> pd.DataFrame:
    """
    Returns a COPY of df with Q110 imputed:
      3 (Not applicable) -> 2 (No)
      777 (Refused)      -> 2 (No)
    Does not modify original df.
    """
    df_imp = df.copy()
    if col in df_imp.columns:
        df_imp[col] = df_imp[col].replace({3: 2, 777: 2})
    return df_imp


def compute_financial_challenges_category(row):
    """
    CF J: Financial Challenges
    Output:
      0 = no
      1 = yes

    Coding:
      If (Q108 = 1 AND Q109 = 1)
         OR (Q110 = 1 AND Q111 = 1)
         OR (Q74 ≤ 2)
      Then: 1 (yes)
      Else: 0 (no)

    Notes:
    - Q108/Q110: 4 or 777 (Refused/X) -> treat as not usable
    - Q74: 777 (Refused/X) -> treat as not usable
    - "Not applicable" responses do NOT trigger "yes"
    """

    q108 = _to_int(row.get(Q108_COL))
    q109 = _to_int(row.get(Q109_COL))
    q110 = _to_int(row.get(Q110_COL))
    q111 = _to_int(row.get(Q111_COL))
    q74  = _to_int(row.get(Q74_COL))

    if q108 in (4, 777): q108 = None
    if q110 in (4, 777): q110 = None
    if q74  in (777,):   q74  = None

    cond_poly_gp = (q108 == 1 and q109 == 1)
    cond_hosp    = (q110 == 1 and q111 == 1)
    cond_q74     = (q74 is not None and q74 <= 2)

    return 1 if (cond_poly_gp or cond_hosp or cond_q74) else 0


def add_financial_challenges_column(df):
    df["Financial_Challenges_CF"] = df.apply(compute_financial_challenges_category, axis=1)
    return df


# -------------------------------
# Imputed CF variant (uses Q110-imputed df)
# -------------------------------
def add_financial_challenges_column_imputed(df):
    """
    Creates a COPY df where Q110 is imputed (3,777 -> 2),
    then computes Financial_Challenges_CF_Imputed using SAME logic.
    """
    df_imp = impute_q110_to_no(df, col=Q110_COL)
    df_imp["Financial_Challenges_CF_Imputed"] = df_imp.apply(compute_financial_challenges_category, axis=1)
    return df_imp


def FinancialChallenges_layout(df):

    # Ensure raw CF exists (if not already computed before calling layout)
    if "Financial_Challenges_CF" not in df.columns:
        df = add_financial_challenges_column(df)

    # Build imputed df (Q110 imputed) + imputed CF
    df_imp = add_financial_challenges_column_imputed(df)

    # -------------------------------
    # Category counts (RAW)
    # -------------------------------
    count_table = pd.DataFrame({
        "Category": [0, 1],
        "Meaning": ["0 = no", "1 = yes"],
        "Count": [
            df["Financial_Challenges_CF"].eq(0).sum(),
            df["Financial_Challenges_CF"].eq(1).sum(),
        ]
    })

    # -------------------------------
    # Category counts (IMPUTED)
    # -------------------------------
    count_table_imputed = pd.DataFrame({
        "Category": [0, 1],
        "Meaning": ["0 = no", "1 = yes"],
        "Count": [
            df_imp["Financial_Challenges_CF_Imputed"].eq(0).sum(),
            df_imp["Financial_Challenges_CF_Imputed"].eq(1).sum(),
        ]
    })

    # -------------------------------
    # Mapping table
    # -------------------------------
    mapping_rows = [
        {
            "Complicating Factor": "J. Financial Challenges",
            "Mapped Question No from Survey": "Q108, Q109, Q110, Q111, Q74",
            "Question Description": (
                "Q108. During the past 12 months, was there a time you did not receive a "
                "consultation / check-up / prescribed treatment at any polyclinic or general practitioner "
                "when you really needed it for your health problem?\n"
                "1) Yes\n"
                "2) No\n"
                "3) Not applicable as there was no need for health care\n"
                "4) X (Refused)\n\n"
                "Q109. What was the main reason for not receiving the consultation / check-up / prescribed "
                "treatment (choose the most applicable option only)?\n"
                "1) Could not afford to (too expensive)\n\n"
                "Q110. During the past 12 months, was there a time you did not receive a consultation / "
                "check-up / prescribed treatment at any public hospital when you really needed it for your health problem?\n"
                "1) Yes\n"
                "2) No\n"
                "3) Not applicable as there was no need for health care\n"
                "4) X (Refused)\n\n"
                "Q111. What was the main reason for not receiving the consultation / check-up / prescribed "
                "treatment (choose the most applicable option only)?\n"
                "1) Could not afford to (too expensive)\n\n"
                "Q74. I / My family have adequate funds to meet my health expenses (inclusive of caregiver expenses).\n"
                "1) Strongly disagree\n"
                "2) Disagree\n"
                "3) Neither\n"
                "4) Agree\n"
                "5) Strongly agree\n"
                "777) X (Refused)"
            ),
            "Levels": "0 = no\n\n1 = yes",
            "Data Mapping": (
                "Q108:\n"
                "  1 = Yes\n"
                "  2 = No\n"
                "  3 = Not applicable (no need for health care)\n"
                "  4 = Refused\n\n"
                "Q109:\n"
                "  1 = Could not afford (too expensive)\n\n"
                "Q110:\n"
                "  1 = Yes\n"
                "  2 = No\n"
                "  3 = Not applicable (no need for health care)\n"
                "  4 = Refused\n\n"
                "Q111:\n"
                "  1 = Could not afford (too expensive)\n\n"
                "Q74:\n"
                "  1 = Strongly disagree\n"
                "  2 = Disagree\n"
                "  3 = Neither agree nor disagree\n"
                "  4 = Agree\n"
                "  5 = Strongly agree\n"
                "  777 = Refused"
            ),

            "Coding": (
                "If (Q108 = 1 AND Q109 = 1)\n"
                "OR (Q110 = 1 AND Q111 = 1)\n"
                "OR (Q74 ≤ 2)\n"
                "Then: 1 (yes)\n\n"
                "Else: 0 (no)"
            ),
        }
    ]
    mapping_table = build_mapping_table(mapping_rows, title="CF J - Financial Challenges")

    # -------------------------------
    # Value counts tables (RAW mapped)
    # -------------------------------
    vc_q108 = build_mapped_value_counts_table(df, Q108_COL, Q108_MAP, sort_by_order=Q108_ORDER)
    vc_q109 = build_mapped_value_counts_table(df, Q109_COL, Q109_MAP, sort_by_order=Q109_ORDER)
    vc_q110 = build_mapped_value_counts_table(df, Q110_COL, Q110_MAP, sort_by_order=Q110_ORDER)
    vc_q111 = build_mapped_value_counts_table(df, Q111_COL, Q111_MAP, sort_by_order=Q111_ORDER)
    vc_q74  = build_mapped_value_counts_table(df, Q74_COL,  Q74_MAP,  sort_by_order=Q74_ORDER)

    # -------------------------------
    # Value counts Q110 (IMPUTED: 3 & 777 -> 2)
    # -------------------------------
    vc_q110_imputed = build_mapped_value_counts_table(
        df_imp, Q110_COL, Q110_MAP, sort_by_order=Q110_ORDER
    )

    # ============================================================
    # Demographics + CF distribution (USE IMPUTED CF)
    # ============================================================
    df_demo = add_age_bins(df_imp, age_col="Q2", out_col="Age_Bin")

    df_demo = add_categorical_labels(
        df_demo,
        mappings={
            "Gender_Label": {"source": "Q4", "map": {1: "Male", 2: "Female"}},
            "Ethnicity_Label": {"source": "Q3", "map": {1: "Chinese", 2: "Malay", 3: "Indian", 4: "Others"}},
        },
    )

    df_demo = build_cf_value_column(
        df_demo,
        source_col="Financial_Challenges_CF_Imputed",
        out_col="Financial_CF_Value",
        allowed_values={0, 1},
    )

    age_order = ["<40", "40–65", "65–85", ">=85"]
    gender_order = ["Male", "Female"]
    eth_order = ["Chinese", "Malay", "Indian", "Others"]

    age_counts, age_fig = cf_distribution_group_cf_on_y(
        df_demo=df_demo,
        cf_col="Financial_CF_Value",
        group_col="Age_Bin",
        group_order=age_order,
        cf_order=[0, 1, 2],
        title="Financial Challenges (Imputed Q110): CF distribution within each Age bin (0/1)",
        legend_title="Age Bin",
    )

    gender_counts, gender_fig = cf_distribution_group_cf_on_y(
        df_demo=df_demo,
        cf_col="Financial_CF_Value",
        group_col="Gender_Label",
        cf_order=[0, 1, 2],
        group_order=gender_order,
        title="Financial Challenges (Imputed Q110): CF distribution within each Gender group (0/1)",
        legend_title="Gender",
    )

    eth_counts, eth_fig = cf_distribution_group_cf_on_y(
        df_demo=df_demo,
        cf_col="Financial_CF_Value",
        cf_order=[0, 1, 2],
        group_col="Ethnicity_Label",
        group_order=eth_order,
        title="Financial Challenges (Imputed Q110): CF distribution within each Ethnicity group (0/1)",
        legend_title="Ethnicity",
    )

    financial_challenges_matrix = build_cf_matrix_pct_n_table(
        df_demo=df_demo,
        cf_col="Financial_Challenges_CF_Imputed",
        category_order=[0, 1],
        category_labels={
            0: "0: No",
            1: "1: Yes",
        },
            title="Complicating Factor: Financial Challenges (%, n)",
    )
    util_tables = build_cf_x_utilization_binned_tables_per_question(
        df_demo=df_demo,
        cf_col="Financial_Challenges_CF_Imputed",
        category_order=[0, 1],
        category_labels={
            0: "0: No",
            1: "1: Yes",
        },
        util_qcodes=["Q78", "Q85", "Q91", "Q93", "Q96", "Q103"],
        util_question_meta=HEALTHCARE_UTILIZATION_QUESTIONS,
        title_prefix="CF J (Financial Challenges) × Healthcare Utilization (0 / 1–2 / 3–5 / 6+)",
        show_pct=True,   # or False if you want only counts
    )
    # ============================================================
    # Healthcare utilization cross (USE IMPUTED CF)
    # ============================================================
    fin_order = [0, 1]
    util_figs = {}

    for qcode in HC_UTIL_QUESTIONS:
        df_demo = build_gp_visits(df_demo, source_col=qcode, out_col="GP_Visits")
        df_demo = add_visit_bins(df_demo, visits_col="GP_Visits", out_col="GP_Visits_Bin")
        meta = HEALTHCARE_UTILIZATION_QUESTIONS.get(qcode, {})
        util_title = meta.get("title", qcode)
        _, fig_util = gp_visits_by_cf_group(
            df_demo,
            cf_col="Financial_Challenges_CF_Imputed",
            cf_order=fin_order,
            title=f"{qcode}: {util_title} - Cross with Financial Challenges (Imputed Q110: 3/777→2)",
        )
        util_figs[qcode] = fig_util

    # -------------------------------
    # Layout
    # -------------------------------
    card_style = {
        "borderRadius": "16px",
        "boxShadow": "0 6px 18px rgba(0,0,0,0.08)",
        "border": "1px solid rgba(0,0,0,0.06)",
        "backgroundColor": "white",
        "padding": "6px",
    }

    return html.Div([
        mapping_table,
        html.Hr(),
        html.H3("Value Counts (Raw Questions)"),
        html.H5("Q108 – Missed polyclinic/GP consultation when needed"),
        dash_table.DataTable(
            data=vc_q108.to_dict("records"),
            columns=[{"name": c, "id": c} for c in vc_q108.columns],
            style_cell={"textAlign": "left"},
            style_header={"fontWeight": "bold"},
        ),
        html.Br(),
        html.H5("Q109 – Main reason (polyclinic/GP)"),
        dash_table.DataTable(
            data=vc_q109.to_dict("records"),
            columns=[{"name": c, "id": c} for c in vc_q109.columns],
            style_cell={"textAlign": "left"},
            style_header={"fontWeight": "bold"},
        ),
        html.Br(),
        html.H5("Q110 – Missed public hospital consultation when needed (RAW)"),
        dash_table.DataTable(
            data=vc_q110.to_dict("records"),
            columns=[{"name": c, "id": c} for c in vc_q110.columns],
            style_cell={"textAlign": "left"},
            style_header={"fontWeight": "bold"},
        ),
        html.Br(),

        html.H5("Q110 – Value Counts (IMPUTED: 3 & 777 → 2 = No)"),
        dash_table.DataTable(
            data=vc_q110_imputed.to_dict("records"),
            columns=[{"name": c, "id": c} for c in vc_q110_imputed.columns],
            style_cell={"textAlign": "left"},
            style_header={"fontWeight": "bold"},
        ),
        html.Br(),

        html.H5("Q111 – Main reason (public hospital)"),
        dash_table.DataTable(
            data=vc_q111.to_dict("records"),
            columns=[{"name": c, "id": c} for c in vc_q111.columns],
            style_cell={"textAlign": "left"},
            style_header={"fontWeight": "bold"},
        ),
        html.Br(),

        html.H5("Q74 – Adequate funds to meet health expenses"),
        dash_table.DataTable(
            data=vc_q74.to_dict("records"),
            columns=[{"name": c, "id": c} for c in vc_q74.columns],
            style_cell={"textAlign": "left"},
            style_header={"fontWeight": "bold"},
        ),
        html.Br(),

        html.Hr(),
        html.H3("Category Counts"),

        html.H5("Category Counts (RAW)"),
        dash_table.DataTable(
            data=count_table.to_dict("records"),
            columns=[{"name": c, "id": c} for c in count_table.columns],
            style_cell={"textAlign": "center"},
            style_header={"fontWeight": "bold"},
        ),
        html.Br(),

        html.H5("Category Counts (IMPUTED Q110: 3 & 777 → 2)"),
        dash_table.DataTable(
            data=count_table_imputed.to_dict("records"),
            columns=[{"name": c, "id": c} for c in count_table_imputed.columns],
            style_cell={"textAlign": "center"},
            style_header={"fontWeight": "bold"},
),
        html.Br(),
        html.Hr(),
        financial_challenges_matrix,
        html.Br(),
        html.Hr(),
        util_tables,
        html.Br(),
        html.Hr(),
        html.H3("Distribution by Demographics (Imputed Q110)"),
        dbc.Card(dbc.CardBody(dcc.Graph(figure=age_fig, config={"displayModeBar": False})), style=card_style),
        html.Br(),
        dbc.Card(dbc.CardBody(dcc.Graph(figure=gender_fig, config={"displayModeBar": False})), style=card_style),
        html.Br(),
        dbc.Card(dbc.CardBody(dcc.Graph(figure=eth_fig, config={"displayModeBar": False})), style=card_style),
        html.Hr(),
        html.H3("Healthcare Utilization: Cross with Financial Challenges (Imputed Q110)"),
        dbc.Row(
            [
                dbc.Col(
                    chart_card(
                        util_figs["Q78"],
                        title="Q78 – Private General Practitioner (GP)",
                    ),
                    md=6,
                ),
                dbc.Col(
                    chart_card(
                        util_figs["Q85"],
                        title="Q85 – Polyclinic doctor visits",
                    ),
                    md=6,
                ),
            ],
            className="mb-4",
        ),

        dbc.Row(
            [
                dbc.Col(
                    chart_card(
                        util_figs["Q91"],
                        title="Q91 – Specialist Outpatient Clinic (SOC) visits",
                    ),
                    md=6,
                ),
                dbc.Col(
                    chart_card(
                        util_figs["Q93"],
                        title="Q93 – Emergency Department (ED) visits",
                    ),
                    md=6,
                ),
            ],
            className="mb-4",
        ),

        dbc.Row(
            [
                dbc.Col(
                    chart_card(
                        util_figs["Q96"],
                        title="Q96 – Public Hospital Admissions",
                    ),
                    md=6,
                ),
                dbc.Col(
                    chart_card(
                        util_figs["Q103"],
                        title="Q103 – Private hospital admissions",
                    ),
                    md=6,
                ),
            ],
        ),
        html.Br(),
    ])
