import pandas as pd
from dash import html, dcc, dash_table
import plotly.express as px
from logic.mapping_helpers import build_mapping_table
from logic.nursing_helper import (nursing_question_group_table, nursing_response_cards)
from logic.demographics_helpers import add_age_bins, add_categorical_labels
from logic.cf_distribution_helpers import build_cf_value_column, cf_distribution_group_cf_on_y
from logic.utilization_helpers import build_gp_visits, add_visit_bins, gp_visits_by_cf_group
from logic.question_texts import HEALTHCARE_UTILIZATION_QUESTIONS
import dash_bootstrap_components as dbc
from logic.cf_matrix_tables import build_cf_matrix_pct_n_table
from logic.utilization import build_cf_x_utilization_binned_tables_per_question
from logic.ui_helpers import chart_card
# --------------------------------------------
# Columns for Rehabilitation Skilled Task Needs
# --------------------------------------------
Q107_rehab_cols = ["Q107_5", "Q107_6", "Q107_7"]
Q107_rehab_labels = [
    "Physiotherapy",
    "Speech therapy",
    "Occupational therapy",
]
HC_UTIL_QUESTIONS = ["Q78", "Q85", "Q91", "Q93", "Q96", "Q103"]

# --------------------------------------------
# Compute Rehab Category
# --------------------------------------------
def compute_rehab_category(row):
    """Compute rehabilitation skilled task needs based on Q107_5–Q107_7."""
    values = row[Q107_rehab_cols].values

    # Keep only valid responses (0 = not mentioned, 1 = mentioned)
    valid = [x for x in values if x in (0, 1)]

    # If all are 999 or missing → no valid info → return None (Not scored)
    if len(valid) == 0:
        return None

    # Count how many tasks are mentioned (value == 1)
    count_mentioned = sum(1 for x in valid if x == 1)

    if count_mentioned == 0:
        return 0   # None
    elif count_mentioned == 1:
        return 1   # Moderate (1 task)
    else:
        return 2   # High (2 or more tasks)


# --------------------------------------------
# Add Rehab Column to Dataset
# --------------------------------------------
def add_rehab_column(df):
    df["Rehab_Needs"] = df.apply(compute_rehab_category, axis=1)
    return df

# --------------------------------------------
# Imputed Column Variant
# --------------------------------------------
def add_rehab_column_imputed(df):
    """
    Creates an imputed version of Rehab_Needs where Q107 999 -> 0,
    then recomputes category using the SAME compute_rehab_category().
    Does NOT modify the original df.
    """
    df_imp = df.copy()

    # Replace 999 -> 0 only for Q107 columns
    for c in Q107_rehab_cols:
        if c in df_imp.columns:
            df_imp[c] = pd.to_numeric(df_imp[c], errors="coerce")
            df_imp[c] = df_imp[c].replace(999, 0)

    # Recompute category using existing logic (unchanged)
    df_imp["Rehab_Needs_Imputed"] = df_imp.apply(compute_rehab_category, axis=1)
    return df_imp

# --------------------------------------------
# Layout Page for Dash
# --------------------------------------------
def Rehab_layout(df):

    table = nursing_question_group_table(
        df,
        cols=Q107_rehab_cols,
        row_labels=Q107_rehab_labels,
        title_text="Q107 – After discharge from your last hospital admission, which of the following did you need?",
    )
    
    count_table = pd.DataFrame({
        "Category": [0, 1, 2],
        "Meaning": [
            "None",
            "Moderate (1 task)",
            "High (2 or more tasks)"
        ],
        "Count": [
            df["Rehab_Needs"].eq(0).sum(),
            df["Rehab_Needs"].eq(1).sum(),
            df["Rehab_Needs"].eq(2).sum(),
        ]
    })

    # -------------------------------
    # AFTER IMPUTATION (999 -> 0)
    # -------------------------------
    df_imp = add_rehab_column_imputed(df)

    count_table_imputed = pd.DataFrame({
        "Category": [0, 1, 2],
        "Meaning": [
            "None",
            "Moderate (1 task)",
            "High (2 or more tasks)"
        ],
        "Count": [
            df_imp["Rehab_Needs_Imputed"].eq(0).sum(),
            df_imp["Rehab_Needs_Imputed"].eq(1).sum(),
            df_imp["Rehab_Needs_Imputed"].eq(2).sum(),
        ]
    })

    # Bar chart
    fig = px.bar(
        count_table,
        x="Meaning",
        y="Count",
        title="Rehabilitation Type Skilled Task Needs Distribution",
        text="Count",
        color="Category"
    )

    mapping_rows = [
        {
            "Complicating Factor": "C. Rehabilitation Type Skilled Task Needs",
            "Mapped Question No from Survey": "Q107",
            "Question Description": (
                "Q107–\n"
                "After discharge from your last hospital admission, which of the following did you need?\n"
                "(5) Physiotherapy\n"
                "(6) Speech therapy\n"
                "(7) Occupational therapy\n"
            ),
            "Levels": (
                "0: None\n\n"
                "1: Moderate (1 task)\n\n"
                "2: High (2 or more tasks)"),
            "Data Mapping": (
                "Q107 -\n 0) Not mentioned\n 1) Mentioned\n 999) Not Applicable\n\n"
            ),
            "Coding": (
            "If Q107_5 to Q107_7 == 0 then\n"
            "0: None\n\n"
            "Count how many of Q107_5 to Q107_7 are 1.\n"
            "If count == 1 then\n"
            "1: Moderate (1 task)\n\n"
            "If count >= 2 then\n"
            "2: High (2 or more tasks)"
        ),
        }
    ]
    mapping_table = build_mapping_table(mapping_rows, title="CF C - Rehabilitation Type Skilled Task Needs")

    # -------------------------------
    # Demographics + CF distribution (IMPUTED df)
    # -------------------------------
    # df_imp already created above and contains Rehab_Needs_Imputed
    df_demo = add_age_bins(df_imp, age_col="Q2", out_col="Age_Bin")

    df_demo = add_categorical_labels(
        df_demo,
        mappings={
            "Gender_Label": {"source": "Q4", "map": {1: "Male", 2: "Female"}},
            "Ethnicity_Label": {"source": "Q3", "map": {1: "Chinese", 2: "Malay", 3: "Indian", 4: "Others"}},
        },
    )

    # Keep original CF levels 0/1/2 for grouping (NOT binary) — use the IMPUTED CF
    df_demo = build_cf_value_column(
        df_demo,
        source_col="Rehab_Needs_Imputed",
        out_col="Rehab_CF_Value",
        allowed_values={0, 1, 2},
    )
    # --------------------------------

    rehab_matrix = build_cf_matrix_pct_n_table(
        df_demo=df_demo,
        cf_col="Rehab_Needs_Imputed",
        category_order=[0, 1, 2],
        category_labels={
            0: "0: None",
            1: "1: Moderate (1 task)",
            2: "2: High (2 or more tasks)",
        },
        title="Complicating Factor: Rehabilitation Type Skilled Task Needs (%, n)",
        total_denominator=2499,
    )

    util_tables = build_cf_x_utilization_binned_tables_per_question(
        df_demo=df_demo,
        cf_col="Rehab_Needs_Imputed",
        category_order=[0, 1, 2],
        category_labels={
            0: "0: None",
            1: "1: Moderate (1 task)",
            2: "2: High (2 or more tasks)",
        },
        util_qcodes=["Q78", "Q85", "Q91", "Q93", "Q96", "Q103"],
        util_question_meta=HEALTHCARE_UTILIZATION_QUESTIONS,
        title_prefix="CF C (Rehab Needs) × Healthcare Utilization (0 / 1–2 / 3–5 / 6+)",
        show_pct=True,   # or False if you want only counts
    )
    # -------------------------------
    # Healthcare utilization: cross with Rehab_Needs (0/1/2)
    # -------------------------------
    rehab_order = [0, 1, 2]
    util_figs = {}
    for qcode in HC_UTIL_QUESTIONS:
        df_demo = build_gp_visits(df_demo, source_col=qcode, out_col="GP_Visits")
        df_demo = add_visit_bins(df_demo, visits_col="GP_Visits", out_col="GP_Visits_Bin")
        meta = HEALTHCARE_UTILIZATION_QUESTIONS.get(qcode, {})
        util_title = meta.get("title", qcode)

        _, fig_util = gp_visits_by_cf_group(
            df_demo,
            cf_col="Rehab_Needs_Imputed",
            cf_order=rehab_order,
            title=f"{qcode}: {util_title} - Cross with Rehabilitation Type Skilled Task Needs (Imputed: 999→0)")
        fig_util.update_layout(legend_title_text=util_title)
        util_figs[qcode] = fig_util

    # -------------------------------
    # CF distribution across demographics (IMPUTED)
    # -------------------------------
    age_counts, age_fig = cf_distribution_group_cf_on_y(
        df_demo=df_demo,
        cf_col="Rehab_Needs_Imputed",
        group_col="Age_Bin",
        cf_order=[0, 1, 2],
        group_order=["<40", "40–65", "65–85", ">=85"],
        title="Rehab Needs: CF distribution within each Age Bin",
        legend_title="CF Category")

    gender_counts, gender_fig = cf_distribution_group_cf_on_y(
        df_demo=df_demo,
        cf_col="Rehab_Needs_Imputed",
        group_col="Gender_Label",
        cf_order=[0, 1, 2],
        group_order=["Male", "Female"],
        title="Rehab Needs: CF distribution within each Gender group",
        legend_title="CF Category")

    eth_counts, eth_fig = cf_distribution_group_cf_on_y(
        df_demo=df_demo,
        cf_col="Rehab_Needs_Imputed",
        group_col="Ethnicity_Label",
        cf_order=[0, 1, 2],
        group_order=["Chinese", "Malay", "Indian", "Others"],
        title="Rehab Needs: CF distribution within each Ethnicity group",
        legend_title="CF Category")

    return html.Div([
        mapping_table,
        html.Br(),
        table,
        html.Br(),
        html.Br(),
        html.Hr(),
        html.H4("Distribution of # of Categories - Rehabilitation Type Skilled Task Needs"),
        html.Hr(),
        html.H4("Category Counts (without imputation)"),
        html.Hr(),
        dash_table.DataTable(
            data=count_table.to_dict("records"),
            columns=[{"name": c, "id": c} for c in count_table.columns],
            style_cell={"textAlign": "center"},
            style_header={"fontWeight": "bold"},),
        html.Br(),
        html.Hr(),
        html.H4("Category Counts (after imputation: 999 → 0)"),
        html.Hr(),
        dash_table.DataTable(
            data=count_table_imputed.to_dict("records"),
            columns=[{"name": c, "id": c} for c in count_table_imputed.columns],
            style_cell={"textAlign": "center"},
            style_header={"fontWeight": "bold"},
        ),
        html.Br(),
        html.Hr(),
        rehab_matrix,
        html.Br(),
        html.Hr(),
        util_tables,
        html.Br(),
        html.Hr(),
        html.H3("Distribution of # of CFs by Demographics (Rehab Needs)"),
        html.Hr(),  
        dbc.Card(
        dbc.CardBody(
            dcc.Graph(figure=age_fig, config={"displayModeBar": False})
        ),
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
            dbc.CardBody(
                dcc.Graph(figure=eth_fig, config={"displayModeBar": False})
            ),
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
        html.H3("Distribution of # of CFs by Utilization (Rehab Needs)"),
        html.Hr(),
        dbc.Row(
            [
                dbc.Col(chart_card(util_figs["Q78"], title="Q78 – Private General Practitioner (GP)"), md=6),
                dbc.Col(chart_card(util_figs["Q85"], title="Q85 – Polyclinic doctor visits"), md=6),
            ],
            className="mb-4",
        ),

        dbc.Row(
            [
                dbc.Col(chart_card(util_figs["Q91"], title="Q91 – Specialist Outpatient Clinic (SOC) visits"), md=6),
                dbc.Col(chart_card(util_figs["Q93"], title="Q93 – Emergency Department (ED) visits"), md=6),
            ],
            className="mb-4",
        ),

        dbc.Row(
            [
                dbc.Col(chart_card(util_figs["Q96"], title="Q96 – Public Hospital Admissions"), md=6),
                dbc.Col(chart_card(util_figs["Q103"], title="Q103 – Private hospital admissions"), md=6),
            ],
            className="mb-4",
        ),
    ])
