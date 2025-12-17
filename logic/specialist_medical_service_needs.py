import pandas as pd
from dash import html, dcc, dash_table
import dash_bootstrap_components as dbc

from logic.mapping_helpers import build_mapping_table
from logic.demographics_helpers import add_age_bins, add_categorical_labels
from logic.cf_distribution_helpers import build_cf_value_column, cf_distribution_rowwise_by_group
from logic.utilization import build_cf_x_utilization_binned_tables_per_question
from logic.utilization_helpers import build_gp_visits, add_visit_bins, gp_visits_by_cf_group
from logic.question_texts import HEALTHCARE_UTILIZATION_QUESTIONS
from logic.global_impressions import assign_gi_label, GI_ASSIGN_ORDER
from logic.cf_matrix_tables import build_cf_matrix_pct_n_table
from logic.ui_helpers import chart_card
# --------------------------------------------
# Constants
# --------------------------------------------
OUT_COL = "Specialist_Medical_Service_Needs_CF"
HC_UTIL_QUESTIONS = ["Q78", "Q85", "Q91", "Q93", "Q96", "Q103"]
CF_ORDER = [0, 1, 2]


def add_specialist_medical_service_needs_column(df: pd.DataFrame) -> pd.DataFrame:
    """
    CF K derived from GI_Assigned:
      0 = no need
      1 = single/occasional referral (GI III or GI IV)
      2 = regular follow-up (GI V)
    """
    dff = df.copy()

    if "GI_Assigned" not in dff.columns:
        dff["GI_Assigned"] = dff.apply(assign_gi_label, axis=1)
        dff["GI_Assigned"] = pd.Categorical(
            dff["GI_Assigned"], categories=GI_ASSIGN_ORDER, ordered=True
        )

    def _map_gi_to_cf_k(gi_label):
        if pd.isna(gi_label):
            return None
        gi_label = str(gi_label).strip()
        if gi_label in ("GI III", "GI IV"):
            return 1
        if gi_label == "GI V":
            return 2
        return 0

    dff[OUT_COL] = dff["GI_Assigned"].apply(_map_gi_to_cf_k)
    return dff


def SpecialistMedicalServiceNeeds_layout(df: pd.DataFrame):
    # Ensure CF exists
    df_cf = add_specialist_medical_service_needs_column(df)

    # -----------------------
    # Mapping table
    # -----------------------
    mapping_rows = [
        {
            "Complicating Factor": "K. Specialist medical service needs",
            "Mapped Question No from Survey": "",
            "Question Description": "",
            "Levels": (
                "0 = no need\n\n"
                "1 = single or occasional referral for advice to the primary physician\n\n"
                "2 = regular follow up by specialist(s) for ongoing care of a condition"
            ),
            "Data Mapping": "Derived from Global Impression (GI_Assigned)",
            "Coding": (
                "If GI_Assigned = 'GI III' OR 'GI IV' then 1\n"
                "Else if GI_Assigned = 'GI V' then 2\n"
                "Else 0"
            ),
        }
    ]
    mapping_table = build_mapping_table(mapping_rows, title="CF K - Specialist medical service needs")

    # -----------------------
    # Category counts
    # -----------------------
    count_table = pd.DataFrame(
        {
            "Category": [0, 1, 2],
            "Meaning": [
                "0 = no need",
                "1 = single or occasional referral for advice to the primary physician",
                "2 = regular follow up by specialist(s) for ongoing care of a condition",
            ],
            "Count": [
                int(df_cf[OUT_COL].eq(0).sum()),
                int(df_cf[OUT_COL].eq(1).sum()),
                int(df_cf[OUT_COL].eq(2).sum()),
            ],
        }
    )

    # -----------------------
    # Demographics prep (optional but matches your pattern)
    # -----------------------
    df_demo = add_age_bins(df_cf, age_col="Q2", out_col="Age_Bin")

    df_demo = add_categorical_labels(
        df_demo,
        mappings={
            "Gender_Label": {"source": "Q4", "map": {1: "Male", 2: "Female"}},
            "Ethnicity_Label": {"source": "Q3", "map": {1: "Chinese", 2: "Malay", 3: "Indian", 4: "Others"}},
        },
    )

    df_demo = build_cf_value_column(
        df_demo,
        source_col=OUT_COL,
        out_col="Specialist_CF_Value",
        allowed_values={0, 1, 2},
    )

    # (Optional) Demographics charts like other CFs
    age_order = ["<40", "40–65", "65–85", ">=85"]
    gender_order = ["Male", "Female"]
    eth_order = ["Chinese", "Malay", "Indian", "Others"]

    _, age_fig = cf_distribution_rowwise_by_group(
        df_demo=df_demo,
        cf_col="Specialist_CF_Value",
        group_col="Age_Bin",
        group_order=age_order,
        cf_order=[0,1,2],
        title="Specialist Medical Service Needs: Distribution by Age",
        legend_title="Age Bin",
    )
    _, gender_fig = cf_distribution_rowwise_by_group(
        df_demo=df_demo,
        cf_col="Specialist_CF_Value",
        group_col="Gender_Label",
        cf_order=[0,1,2],
        group_order=gender_order,
        title="Specialist Medical Service Needs: Distribution by Gender",
        legend_title="Gender",
    )
    _, eth_fig = cf_distribution_rowwise_by_group(
        df_demo=df_demo,
        cf_col="Specialist_CF_Value",
        cf_order=[0,1,2],
        group_col="Ethnicity_Label",
        group_order=eth_order,
        title="Specialist Medical Service Needs: Distribution by Ethnicity",
        legend_title="Ethnicity",
    )

    specialist_matrix = build_cf_matrix_pct_n_table(
        df_demo=df_demo,
        cf_col="Specialist_CF_Value",
        category_order=[0, 1, 2],
        category_labels={
            0: "0: no need",
            1: "1: single or occasional referral for advice to the primary physician",
            2: "2: regular follow up by specialist(s) for ongoing care of a condition",
        },
            title="Complicating Factor: Specialist Medical Service Needs (%, n)",
    )
    util_tables = build_cf_x_utilization_binned_tables_per_question(
        df_demo=df_demo,
        cf_col="Specialist_CF_Value",
        category_order=[0, 1],
        category_labels={
            0: "0: no need",
            1: "1: single or occasional referral for advice to the primary physician",
            2: "2: regular follow up by specialist(s) for ongoing care of a condition",
        },
        util_qcodes=["Q78", "Q85", "Q91", "Q93", "Q96", "Q103"],
        util_question_meta=HEALTHCARE_UTILIZATION_QUESTIONS,
        title_prefix="CF K (Specialist Medical Service Needs) × Healthcare Utilization (0 / 1–2 / 3–5 / 6+)",
        show_pct=True,   # or False if you want only counts
    )
    # -----------------------
    # Utilization charts (same as other CFs)
    # -----------------------
    util_figs = {}
    for qcode in HC_UTIL_QUESTIONS:
        df_demo = build_gp_visits(df_demo, source_col=qcode, out_col="GP_Visits")
        df_demo = add_visit_bins(df_demo, visits_col="GP_Visits", out_col="GP_Visits_Bin")

        meta = HEALTHCARE_UTILIZATION_QUESTIONS.get(qcode, {})
        util_title = meta.get("title", qcode)

        _, fig_util = gp_visits_by_cf_group(
            df_demo,
            cf_col=OUT_COL,          # <-- CF K column
            cf_order=CF_ORDER,       # [0,1,2]
            title=f"{qcode}: {util_title} - Cross with Specialist Medical Service Needs (CF K)",
        )
        util_figs[qcode] = fig_util

    # -----------------------
    # Layout
    # -----------------------
    return html.Div(
        [
            mapping_table,
            html.Br(),
            html.H4("Category Counts"),
            dash_table.DataTable(
                data=count_table.to_dict("records"),
                columns=[{"name": c, "id": c} for c in count_table.columns],
                style_cell={"textAlign": "center"},
                style_header={"fontWeight": "bold"},
            ),
            html.Br(),
            html.Hr(),
            specialist_matrix,
            html.Br(),
            html.Hr(),
            util_tables,
            html.Br(),
            html.Hr(),
            html.H3("Distribution of # of CFs by Demographics - Specialist Medical Service Needs"),
            html.Hr(),

            dbc.Card(dbc.CardBody(dcc.Graph(figure=age_fig, config={"displayModeBar": False})),
                     style={"borderRadius": "16px", "boxShadow": "0 6px 18px rgba(0,0,0,0.08)",
                            "border": "1px solid rgba(0,0,0,0.06)", "backgroundColor": "white", "padding": "6px"}),
            html.Br(),

            dbc.Card(dbc.CardBody(dcc.Graph(figure=gender_fig, config={"displayModeBar": False})),
                     style={"borderRadius": "16px", "boxShadow": "0 6px 18px rgba(0,0,0,0.08)",
                            "border": "1px solid rgba(0,0,0,0.06)", "backgroundColor": "white", "padding": "6px"}),
            html.Br(),

            dbc.Card(dbc.CardBody(dcc.Graph(figure=eth_fig, config={"displayModeBar": False})),
                     style={"borderRadius": "16px", "boxShadow": "0 6px 18px rgba(0,0,0,0.08)",
                            "border": "1px solid rgba(0,0,0,0.06)", "backgroundColor": "white", "padding": "6px"}),

            html.Br(),
            html.Hr(),
            html.H3("Distribution of # of CFs by Utilization - Specialist Medical Service Needs"),
            html.Hr(),
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

        ]
    )
