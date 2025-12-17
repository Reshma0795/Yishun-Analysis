import pandas as pd
from dash import html, dcc, dash_table
import plotly.express as px
from logic.question_texts import HEALTHCARE_UTILIZATION_QUESTIONS
from logic.utilization import build_cf_x_utilization_binned_tables_per_question
from logic.value_counts_helpers import build_value_counts_table
from logic.mapping_helpers import build_mapping_table
import dash_bootstrap_components as dbc

from logic.demographics_helpers import add_age_bins, add_categorical_labels
from logic.cf_distribution_helpers import build_cf_value_column, cf_distribution_rowwise_by_group
from logic.utilization_helpers import build_gp_visits, add_visit_bins, gp_visits_by_cf_group
from logic.cf_matrix_tables import build_cf_matrix_pct_n_table
from logic.ui_helpers import chart_card
# --------------------------------------------
# Columns (Q96 main, Q103 optional for display)
# --------------------------------------------
HOSPITAL_MAIN_COL = "Q96"
HOSPITAL_EXTRA_COLS = ["Q103"]  # include in table for reference, even if unused in logic

HC_UTIL_QUESTIONS = ["Q78", "Q85", "Q91", "Q93", "Q96", "Q103"]

# --------------------------------------------
# Compute Hospital Admissions CF
# --------------------------------------------
def compute_hospital_category(row):
    """
    Compute 'Hospital admissions in last 6 months' CF based on Q96.

    Raw mapping:
        Q96:
          0   → 0 = none
          1-2 → 1 = 1 or 2
          >=3 → 2 = 3 or more
          666 / 777 → no score (None)
    """
    val = row[HOSPITAL_MAIN_COL]

    # Handle missing / special codes
    if pd.isna(val):
        return None

    try:
        v = int(val)
    except (TypeError, ValueError):
        return None

    if v in (666, 777):
        return None

    if v == 0:
        return 0
    elif v in (1, 2):
        return 1
    elif v >= 3:
        return 2

    # Fallback
    return None
# --------------------------------------------
# Add Column to DataFrame
# --------------------------------------------
def add_hospital_column(df):
    df["Hospital_Admissions_CF"] = df.apply(compute_hospital_category, axis=1)
    return df
# --------------------------------------------
# Layout for Dash Page
# --------------------------------------------
def Hospital_layout(df):
    # -------------------------------
    # Value counts table for raw Q96 (no imputation)
    # -------------------------------
    q96_vc = build_value_counts_table(
        df,
        col=HOSPITAL_MAIN_COL,
        include_missing=True,
        sort_numeric=True,
        missing_label="Missing",
    )

    count_table = pd.DataFrame({
        "Category": [0, 1, 2],
        "Meaning": [
            "0 = none",
            "1 = 1 or 2 hospital admissions",
            "2 = 3 or more hospital admissions"
        ],
        "Count": [
            df["Hospital_Admissions_CF"].eq(0).sum(),
            df["Hospital_Admissions_CF"].eq(1).sum(),
            df["Hospital_Admissions_CF"].eq(2).sum(),
        ]
    })

    # Bar chart
    fig = px.bar(
        count_table,
        x="Meaning",
        y="Count",
        title="H. Hospital Admissions in Last 12 Months – Distribution",
        text="Count",
        color="Category"
    )

    # Raw data table (show Q96, Q103, and CF)
    display_cols = ["Hospital_Admissions_CF", HOSPITAL_MAIN_COL] + HOSPITAL_EXTRA_COLS

    # Filter to only existing columns (in case Q103 doesn't exist)
    display_cols = [c for c in display_cols if c in df.columns]

    mapping_rows = [
    {
        "Complicating Factor": "H. Hospital admissions in last 6 months",
        "Mapped Question No from Survey": "Q96",
        "Question Description": (
            "Q96. In the past 12 months, how many times have you had public hospital admissions "
            "including public community hospital admissions"
        ),
        "Levels": (
            "0 = none\n\n"
            "1 = 1 or 2\n\n"
            "2 = 3 or more"
        ),
        "Data Mapping": (
            "Q96 –\n"
            " 666) Unable to recall\n"
            " 777) X (Refused)"
        ),
        "Coding": (
            "If Q96 == 0 then\n"
            "0: None\n\n"
            "If Q96 == 1 OR Q96 == 2 then\n"
            "1: 1 or 2\n\n"
            "If Q96 ≥ 3 then\n"
            "2: 3 or more"
        ),
    }
]

    mapping_table = build_mapping_table(mapping_rows, title="CF H - Hospital admissions in last 6 months")
    # -------------------------------
    # Demographics + CF distribution (Hospital Admissions CF: 0/1/2)
    # -------------------------------
    df_demo = add_age_bins(df, age_col="Q2", out_col="Age_Bin")

    df_demo = add_categorical_labels(
        df_demo,
        mappings={
            "Gender_Label": {"source": "Q4", "map": {1: "Male", 2: "Female"}},
            "Ethnicity_Label": {"source": "Q3", "map": {1: "Chinese", 2: "Malay", 3: "Indian", 4: "Others"}},
        },
    )

    # Keep CF levels 0/1/2 for grouping (NOT binary)
    df_demo = build_cf_value_column(
        df_demo,
        source_col="Hospital_Admissions_CF",
        out_col="Hospital_CF_Value",
        allowed_values={0, 1, 2},
    )

    age_order = ["<40", "40–65", "65–85", ">=85"]
    gender_order = ["Male", "Female"]
    eth_order = ["Chinese", "Malay", "Indian", "Others"]

    age_counts, age_fig = cf_distribution_rowwise_by_group(
        df_demo=df_demo,
        cf_col="Hospital_CF_Value",
        group_col="Age_Bin",
        group_order=age_order,
        cf_order=[0, 1, 2],
        title="Hospital Admissions (CF H): Distribution by Age Bin (0/1/2)",
        legend_title="Age Bin",
    )

    gender_counts, gender_fig = cf_distribution_rowwise_by_group(
        df_demo=df_demo,
        cf_col="Hospital_CF_Value",
        group_col="Gender_Label",
        group_order=gender_order,
        cf_order=[0, 1, 2],
        title="Hospital Admissions (CF H): Distribution by Gender (0/1/2)",
        legend_title="Gender",
    )

    eth_counts, eth_fig = cf_distribution_rowwise_by_group(
        df_demo=df_demo,
        cf_col="Hospital_CF_Value",
        group_col="Ethnicity_Label",
        group_order=eth_order,
        cf_order=[0, 1, 2],
        title="Hospital Admissions (CF H): Distribution by Ethnicity (0/1/2)",
        legend_title="Ethnicity",
    )

    hospital_admissions_matrix = build_cf_matrix_pct_n_table(
        df_demo=df_demo,
        cf_col="Hospital_Admissions_CF",
        category_order=[0, 1, 2],
        category_labels={
            0: "0: None",
            1: "1: 1 or 2",
            2: "2: 3 or more",
        },
            title="Complicating Factor: Hospital Admissions (%, n)",
    )

    util_tables = build_cf_x_utilization_binned_tables_per_question(
        df_demo=df_demo,
        cf_col="Hospital_Admissions_CF",
        category_order=[0, 1, 2],
        category_labels={
            0: "0: None",
            1: "1: 1 or 2",
            2: "2: 3 or more",
        },
        util_qcodes=["Q78", "Q85", "Q91", "Q93", "Q96", "Q103"],
        util_question_meta=HEALTHCARE_UTILIZATION_QUESTIONS,
        title_prefix="CF I (Hospital Admissions) × Healthcare Utilization (0 / 1–2 / 3–5 / 6+)",
        show_pct=True,   # or False if you want only counts
    )
    # -------------------------------
    # Healthcare utilization: cross with Hospital_Admissions_CF (0/1/2)
    # -------------------------------
    hospital_order = [0, 1, 2]
    util_figs = {}

    for qcode in HC_UTIL_QUESTIONS:
        df_demo = build_gp_visits(df_demo, source_col=qcode, out_col="GP_Visits")
        df_demo = add_visit_bins(df_demo, visits_col="GP_Visits", out_col="GP_Visits_Bin")
        
        meta = HEALTHCARE_UTILIZATION_QUESTIONS.get(qcode, {})
        util_title = meta.get("title", qcode)
        _, fig_util = gp_visits_by_cf_group(
            df_demo,
            cf_col="Hospital_Admissions_CF",
            cf_order=hospital_order,
            title=f"{qcode}: {util_title} - Cross with Hospital Admissions CF (0/1/2)",
        )
        util_figs[qcode] = fig_util

    return html.Div([
        mapping_table,
        html.H4("Q96 – Value Counts (Raw Responses)"),
        dash_table.DataTable(
            data=q96_vc.to_dict("records"),
            columns=[{"name": c, "id": c} for c in q96_vc.columns],
            style_cell={"textAlign": "center", "padding": "8px"},
            style_header={"fontWeight": "bold", "backgroundColor": "#5b3fd3", "color": "white"},
            style_table={"borderRadius": "12px", "overflow": "hidden"},
        ),
        html.Br(),

        # Optional chart
        # dcc.Graph(figure=q96_vc_fig),
        # html.Br(),
        html.Hr(),
        dash_table.DataTable(
            data=count_table.to_dict("records"),
            columns=[{"name": c, "id": c} for c in count_table.columns],
            style_cell={"textAlign": "center"},
            style_header={"fontWeight": "bold"},
        ),
        html.Br(),
        #html.H4("Distribution Chart"),
        #dcc.Graph(figure=fig),
        html.Hr(),
        hospital_admissions_matrix,
        html.Br(),
        html.Hr(),
        util_tables,
        html.Br(),
        html.Hr(),
        html.H3("Distribution of Hospital Admissions CF by Demographics (0/1/2)"),
        dbc.Card(
            dbc.CardBody(dcc.Graph(figure=age_fig, config={"displayModeBar": False})),
            style={
                "borderRadius": "16px",
                "boxShadow": "0 6px 18px rgba(0,0,0,0.08)",
                "border": "1px solid rgba(0,0,0,0.06)",
                "backgroundColor": "white",
                "padding": "6px",
            },
        ),
        html.Br(),
        dbc.Card(
            dbc.CardBody(dcc.Graph(figure=gender_fig, config={"displayModeBar": False})),
            style={
                "borderRadius": "16px",
                "boxShadow": "0 6px 18px rgba(0,0,0,0.08)",
                "border": "1px solid rgba(0,0,0,0.06)",
                "backgroundColor": "white",
                "padding": "6px",
            },
        ),
        html.Br(),
        dbc.Card(
            dbc.CardBody(dcc.Graph(figure=eth_fig, config={"displayModeBar": False})),
            style={
                "borderRadius": "16px",
                "boxShadow": "0 6px 18px rgba(0,0,0,0.08)",
                "border": "1px solid rgba(0,0,0,0.06)",
                "backgroundColor": "white",
                "padding": "6px",
            },
        ),
        html.Br(),
        html.Hr(),
        html.H3("Healthcare Utilization: Cross with Hospital Admissions CF"),
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

        html.Br()
    ])
