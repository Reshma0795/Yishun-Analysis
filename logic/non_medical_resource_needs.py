import pandas as pd
from dash import html, dcc, dash_table
import plotly.express as px
import dash_bootstrap_components as dbc

from logic.question_texts import HEALTHCARE_UTILIZATION_QUESTIONS
from logic.mapping_helpers import build_mapping_table
from logic.non_medical_value_counts_helpers import build_mapped_value_counts_table

from logic.demographics_helpers import add_age_bins, add_categorical_labels
from logic.cf_distribution_helpers import build_cf_value_column, cf_distribution_rowwise_by_group
from logic.utilization import build_cf_x_utilization_binned_tables_per_question
from logic.utilization_helpers import build_gp_visits, add_visit_bins, gp_visits_by_cf_group
from logic.cf_matrix_tables import build_cf_matrix_pct_n_table
from logic.ui_helpers import chart_card
# ------------------------------------------------------------
# L. Non-medical resource needs (Q185)
# ------------------------------------------------------------

Q185_EVENT_COLS = [f"Q185_{i}" for i in range(1, 13)]   # Q185_1..Q185_12
Q185_NA_COL = "Q185_13"                                 # Q185_13: 1 = Not applicable

HC_UTIL_QUESTIONS = ["Q78", "Q85", "Q91", "Q93", "Q96", "Q103"]


def _to_int(x):
    if pd.isna(x):
        return None
    try:
        return int(x)
    except (TypeError, ValueError):
        return None


def compute_non_medical_resource_needs_category(row):
    """
    CF L:
      0 = stable/secure
      1 = intermittent concerns
      2 = major ongoing problems

    Coding:
      - If (Q185_1..Q185_12 all 0) AND (Q185_13 == 1) -> 0
      - If (Q185_4 == 1) OR (Q185_7 == 1) OR (Q185_8 == 1) -> 2
      - Else -> 1

    Notes:
      - 777 treated as unusable for that item.
      - If everything is unusable/missing -> None
    """
    vals = [_to_int(row.get(c)) for c in Q185_EVENT_COLS]
    na_flag = _to_int(row.get(Q185_NA_COL))

    if all(v is None for v in vals) and na_flag is None:
        return None

    usable_vals = [v for v in vals if v is not None and v != 777]

    if na_flag == 1 and len(usable_vals) > 0 and all(v == 0 for v in usable_vals):
        return 0

    q185_4 = _to_int(row.get("Q185_4"))
    q185_7 = _to_int(row.get("Q185_7"))
    q185_8 = _to_int(row.get("Q185_8"))

    if q185_4 == 1 or q185_7 == 1 or q185_8 == 1:
        return 2

    if any(v == 1 for v in usable_vals):
        return 1

    if len(usable_vals) > 0:
        return 1

    return None


def add_non_medical_resource_needs_column(df):
    if "Non_Medical_Resource_Needs_CF" not in df.columns:
        df["Non_Medical_Resource_Needs_CF"] = df.apply(
            compute_non_medical_resource_needs_category, axis=1
        )
    return df


def NonMedicalResourceNeeds_layout(df):
    df = add_non_medical_resource_needs_column(df)

    # -------------------------------
    # Category counts
    # -------------------------------
    count_table = pd.DataFrame(
        {
            "Category": [0, 1, 2],
            "Meaning": [
                "0: has stable and secure access to all areas of social determinants of health",
                "1: has some, intermittent concerns with at least one area of social determinants of health",
                "2: has major ongoing problems with at least one area of social determinants of health",
            ],
            "Count": [
                df["Non_Medical_Resource_Needs_CF"].eq(0).sum(),
                df["Non_Medical_Resource_Needs_CF"].eq(1).sum(),
                df["Non_Medical_Resource_Needs_CF"].eq(2).sum(),
            ],
        }
    )

    # -------------------------------
    # Mapping table
    # -------------------------------
    mapping_rows = [
        {
            "Complicating Factor": "L. Non-medical resource needs",
            "Mapped Question No from Survey": "Q185",
            "Question Description": (
                "Interviewer: The following list of events is extremely stressful and upsetting events "
                "that sometimes occur to people.\n"
                "Can you indicate which, if any, of these events have you experienced in your life, "
                "over the past year? Check (✓) items that apply.\n\n"
                "Q185:\n"
                "1) Spouse/ partner passing away\n"
                "2) Spouse/partner have life threatening illness or accident\n"
                "3) A family or close friend passing away/diagnosed with life threatening illness or accident (other than your spouse or partner)\n"
                "4) Had major problems with money\n"
                "5) Divorced or breakup\n"
                "6) Major conflict with parents, spouse, children or grandchildren\n"
                "7) Major accidents/ disasters/muggings/unwanted sexual experiences/ robberies\n"
                "8) Physical abused or threatened\n"
                "9) Verbally abused\n"
                "10) Pet died\n"
                "11) Family member/Close friend lost job/retire\n"
                "12) Others\n"
                "13) Not applicable\n"
                "777) Refused"
            ),
            "Levels": (
                "0: has stable and secure access to all areas of social determinants of health\n\n"
                "1: has some, intermittent concerns with at least one area of social determinants of health\n\n"
                "2: has major ongoing problems with at least one area of social determinants of health"
            ),
            "Data Mapping": (
                "Q185_1 to Q185_13 –\n"
                " 0) Not mentioned\n"
                " 1) Mentioned\n"
                " 777) Refused\n\n"
            ),
            "Coding": (
                "If (Q185_1 to Q185_12 = 0) AND (Q185_13 = 1) then\n"
                "0: stable and secure access\n\n"
                "If (Q185_4 = 1) OR (Q185_7 = 1) OR (Q185_8 = 1) then\n"
                "2: major ongoing problems\n\n"
                "Else\n"
                "1: intermittent concerns"
            ),
        }
    ]
    mapping_table = build_mapping_table(mapping_rows, title="CF L - Non-medical resource needs")

    # -------------------------------
    # Value counts tables for Q185_1..Q185_13
    # -------------------------------
    # Mapping for Q185_1..Q185_12
    EVENT_MAP = {
        0: "Not mentioned",
        1: "Mentioned",
        777: "Refused",
    }
    EVENT_ORDER = [0, 1, 777]

    # Mapping for Q185_13
    NA_MAP = {
        1: "Not applicable (checked)",
        0: "Not checked / blank",
        777: "Refused",
    }
    NA_ORDER = [0, 1, 777]

    value_count_blocks = []

    # Q185_1..Q185_12
    for col in Q185_EVENT_COLS:
        vc_df = build_mapped_value_counts_table(
            df, col, EVENT_MAP, sort_by_order=EVENT_ORDER, include_missing=True
        )
        value_count_blocks.append(
            dbc.Card(
                dbc.CardBody(
                    [
                        html.H5(col),
                        dash_table.DataTable(
                            data=vc_df.to_dict("records"),
                            columns=[{"name": c, "id": c} for c in vc_df.columns],
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
                            style_table={"borderRadius": "12px", "overflow": "hidden"},
                            page_size=10,
                        ),
                    ]
                ),
                style={
                    "borderRadius": "16px",
                    "boxShadow": "0 6px 18px rgba(0,0,0,0.08)",
                    "border": "1px solid #eee",
                    "marginBottom": "12px",
                },
            )
        )

    # Q185_13
    if Q185_NA_COL in df.columns:
        vc_na = build_mapped_value_counts_table(
            df, Q185_NA_COL, NA_MAP, sort_by_order=NA_ORDER, include_missing=True
        )
        value_count_blocks.append(
            dbc.Card(
                dbc.CardBody(
                    [
                        html.H5("Q185_13 (Not applicable flag)"),
                        dash_table.DataTable(
                            data=vc_na.to_dict("records"),
                            columns=[{"name": c, "id": c} for c in vc_na.columns],
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
                            style_table={"borderRadius": "12px", "overflow": "hidden"},
                            page_size=10,
                        ),
                    ]
                ),
                style={
                    "borderRadius": "16px",
                    "boxShadow": "0 6px 18px rgba(0,0,0,0.08)",
                    "border": "1px solid #eee",
                    "marginBottom": "12px",
                },
            )
        )

    # ============================================================
    # Demographics distribution (0/1/2)
    # ============================================================
    df_demo = add_age_bins(df, age_col="Q2", out_col="Age_Bin")
    df_demo = add_categorical_labels(
        df_demo,
        mappings={
            "Gender_Label": {"source": "Q4", "map": {1: "Male", 2: "Female"}},
            "Ethnicity_Label": {"source": "Q3", "map": {1: "Chinese", 2: "Malay", 3: "Indian", 4: "Others"}},
        },
    )

    df_demo = build_cf_value_column(
        df_demo,
        source_col="Non_Medical_Resource_Needs_CF",
        out_col="NonMed_CF_Value",
        allowed_values={0, 1, 2},
    )

    age_order = ["<40", "40–65", "65–85", ">=85"]
    gender_order = ["Male", "Female"]
    eth_order = ["Chinese", "Malay", "Indian", "Others"]

    age_counts, age_fig = cf_distribution_rowwise_by_group(
        df_demo=df_demo,
        cf_col="NonMed_CF_Value",
        group_col="Age_Bin",
        cf_order=[0, 1, 2],
        group_order=age_order,
        title="Non-medical Resource Needs: Distribution by Age Bin (0/1/2)",
        legend_title="Age Bin",
    )

    gender_counts, gender_fig = cf_distribution_rowwise_by_group(
        df_demo=df_demo,
        cf_col="NonMed_CF_Value",
        group_col="Gender_Label",
        cf_order=[0, 1, 2],
        group_order=gender_order,
        title="Non-medical Resource Needs: Distribution by Gender (0/1/2)",
        legend_title="Gender",
    )

    eth_counts, eth_fig = cf_distribution_rowwise_by_group(
        df_demo=df_demo,
        cf_col="NonMed_CF_Value",
        group_col="Ethnicity_Label",
        cf_order=[0, 1, 2],
        group_order=eth_order,
        title="Non-medical Resource Needs: Distribution by Ethnicity (0/1/2)",
        legend_title="Ethnicity",
    )

    non_medical_needs_matrix = build_cf_matrix_pct_n_table(
        df_demo=df_demo,
        cf_col="Non_Medical_Resource_Needs_CF",
        category_order=[0, 1, 2],
        category_labels={
            0: "0: has stable and secure access to all areas of social determinants of health",
            1: "1: has some, intermittent concerns with at least one area of social determinants of health",
            2: "2: has major ongoing problems with at least one area of social determinants of health",
        },
            title="Complicating Factor: Non-medical Resource Needs (%, n)",
    )
    util_tables = build_cf_x_utilization_binned_tables_per_question(
        df_demo=df_demo,
        cf_col="Non_Medical_Resource_Needs_CF",
        category_order=[0, 1, 2],
        category_labels={
            0: "0: has stable and secure access to all areas of social determinants of health",
            1: "1: has some, intermittent concerns with at least one area of social determinants of health",
            2: "2: has major ongoing problems with at least one area of social determinants of health",
        },
        util_qcodes=["Q78", "Q85", "Q91", "Q93", "Q96", "Q103"],
        util_question_meta=HEALTHCARE_UTILIZATION_QUESTIONS,
        title_prefix="CF L (Non-medical Resource Needs) × Healthcare Utilization (0 / 1–2 / 3–5 / 6+)",
        show_pct=True,   # or False if you want only counts
    )

    # ============================================================
    # Healthcare utilization cross (0/1/2)
    # ============================================================
    cf_order = [0, 1, 2]
    util_figs = {}

    for qcode in HC_UTIL_QUESTIONS:
        df_demo = build_gp_visits(df_demo, source_col=qcode, out_col="GP_Visits")
        df_demo = add_visit_bins(df_demo, visits_col="GP_Visits", out_col="GP_Visits_Bin")
        meta = HEALTHCARE_UTILIZATION_QUESTIONS.get(qcode, {})
        util_title = meta.get("title", qcode)
        _, fig_util = gp_visits_by_cf_group(
            df_demo,
            cf_col="Non_Medical_Resource_Needs_CF",
            cf_order=cf_order,
            title=f"{qcode}: {util_title} - Cross with Non-medical Resource Needs (0/1/2)",
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

    return html.Div(
        [
            mapping_table,

            html.Hr(),
            html.H3("Value Counts (Q185_1 to Q185_13)"),
            *value_count_blocks,

            html.Hr(),
            html.H4("Category Counts"),
            dash_table.DataTable(
                data=count_table.to_dict("records"),
                columns=[{"name": c, "id": c} for c in count_table.columns],
                style_cell={"textAlign": "center"},
                style_header={"fontWeight": "bold"},
            ),
            html.Br(),
            html.Hr(),
            non_medical_needs_matrix,
            html.Br(),
            html.Hr(),
            util_tables,
            html.Br(),
            html.Hr(),
            html.H3("Distribution by Demographics (0/1/2)"),
            dbc.Card(dbc.CardBody(dcc.Graph(figure=age_fig, config={"displayModeBar": False})), style=card_style),
            html.Br(),
            dbc.Card(dbc.CardBody(dcc.Graph(figure=gender_fig, config={"displayModeBar": False})), style=card_style),
            html.Br(),
            dbc.Card(dbc.CardBody(dcc.Graph(figure=eth_fig, config={"displayModeBar": False})), style=card_style),
            html.Br(),

            html.Hr(),
            html.H3("Healthcare Utilization: Cross with Non-medical Resource Needs"),
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

        ],
        style={"width": "100%", "padding": "0 16px"}

    )
