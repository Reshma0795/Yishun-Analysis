import pandas as pd
from dash import html, dcc, dash_table
import plotly.express as px
from logic.mapping_helpers import build_mapping_table
from logic.nursing_helper import  (nursing_question_group_table, nursing_response_cards)
from logic.demographics_helpers import add_age_bins, add_categorical_labels
from logic.cf_distribution_helpers import build_cf_value_column, cf_distribution_rowwise_by_group
from logic.utilization_helpers import build_gp_visits, add_visit_bins, gp_visits_by_cf_group
from logic.question_texts import HEALTHCARE_UTILIZATION_QUESTIONS
import dash_bootstrap_components as dbc
from logic.cf_matrix_tables import build_cf_matrix_row_pct_n_table
from logic.cf_utilization_crosstab_tables import build_cf_x_utilization_crosstab_table
from logic.cf_utilization_tables import build_cf_x_utilization_binned_table
from logic.utilization import build_cf_x_utilization_binned_tables_per_question
from logic.ui_helpers import chart_card
# --------------------------------------------
# Columns for Nursing Skilled Task Needs
# --------------------------------------------
Q107_cols = ["Q107_1", "Q107_2", "Q107_3", "Q107_4"]
Q107_labels = [
    "Wound dressing",
    "Injections",
    "Change of feeding tube",
    "Change of urinary catheter",]
HC_UTIL_QUESTIONS = ["Q78", "Q85", "Q91", "Q93", "Q96", "Q103"]

# --------------------------------------------
# Compute Nursing Category
# --------------------------------------------
def compute_nursing_category(row):
    """Compute nursing skilled task needs based on Q107."""
    values = row[Q107_cols].values

    # Keep only valid responses (0 = not mentioned, 1 = mentioned)
    valid = [x for x in values if x in (0, 1)]

    # If all are 999 or missing → no valid info → return None (Not scored)
    if len(valid) == 0:
        return None

    count_mentioned = sum(1 for x in valid if x == 1)

    if count_mentioned == 0:
        return 0   # None
    elif count_mentioned == 1:
        return 1   # Moderate (1 task)
    else:
        return 2   # High (2 or more tasks)
    

FA_LEGEND_LABELS = {
    "0": "0: None",
    "1": "1: Moderate (1 task)",
    "2": "2: High (2 or more tasks)",
    "0.0": "0: None",
    "1.0": "1: Moderate (1 task)",
    "2.0": "2: High (2 or more tasks)",
}

def rename_fa_legend(fig):
    fig.for_each_trace(
        lambda t: t.update(name=FA_LEGEND_LABELS.get(str(t.name), t.name))
    )
    return fig


# --------------------------------------------
# Add Column to Dataset
# --------------------------------------------
def add_nursing_column(df):
    df["Nursing_Needs"] = df.apply(compute_nursing_category, axis=1)
    return df

# --------------------------------------------
# Imputed Column Variant
# --------------------------------------------
def add_nursing_column_imputed(df):
    """
    Creates an imputed version of Nursing_Needs where Q107 999 -> 0,
    then recomputes category using the SAME compute_nursing_category().
    Does NOT modify the original df.
    """
    df_imp = df.copy()

    # Replace 999 -> 0 only for Q107 columns
    for c in Q107_cols:
        if c in df_imp.columns:
            df_imp[c] = pd.to_numeric(df_imp[c], errors="coerce")
            df_imp[c] = df_imp[c].replace(999, 0)

    # Recompute category using existing logic (unchanged)
    df_imp["Nursing_Needs_Imputed"] = df_imp.apply(compute_nursing_category, axis=1)
    return df_imp

# --------------------------------------------
# Layout Page for Dash
# --------------------------------------------
def Nursing_layout(df):

    table = nursing_question_group_table(
        df,
        cols=Q107_cols,
        row_labels=Q107_labels,
        title_text="Q107 – After discharge from your last hospital admission, which of the following did you need?",)

    cards = nursing_response_cards(
        df,
        cols=Q107_cols,
        title_prefix="Q107 – Nursing type skilled task needs",)

    count_table = pd.DataFrame({
        "Category": [0, 1, 2],
        "Meaning": [
            "None",
            "Moderate (1 task)",
            "High (2 or more tasks)"
        ],
        "Count": [
            df["Nursing_Needs"].eq(0).sum(),
            df["Nursing_Needs"].eq(1).sum(),
            df["Nursing_Needs"].eq(2).sum(),
        ]
    })

    # -------------------------------
    # AFTER IMPUTATION (999 -> 0)
    # -------------------------------
    df_imp = add_nursing_column_imputed(df)

    count_table_imputed = pd.DataFrame({
        "Category": [0, 1, 2],
        "Meaning": [
            "None",
            "Moderate (1 task)",
            "High (2 or more tasks)"
        ],
        "Count": [
            df_imp["Nursing_Needs_Imputed"].eq(0).sum(),
            df_imp["Nursing_Needs_Imputed"].eq(1).sum(),
            df_imp["Nursing_Needs_Imputed"].eq(2).sum(),
        ]
    })

    fig = px.bar(
        count_table,
        x="Meaning",
        y="Count",
        title="Nursing Type Skilled Task Needs Distribution",
        text="Count",
        color="Category"
    )
    
    mapping_rows = [
        {
            "Complicating Factor": "B. Nursing Type Skilled Task Needs",
            "Mapped Question No from Survey": "Q107",
            "Question Description": (
                "Q107–\n"
                "After discharge from your last hospital admission, which of the following did you need?\n"
                "(1) Wound dressing\n"
                "(2) Dressing\n"
                "(3) Transferring\n"
                "(4) Using the toilet\n"
            ),
            "Levels": (
                "0: None\n\n"
                "1: Moderate (1 task)\n\n"
                "2: High (2 or more tasks)"),
            "Data Mapping": (
                "Q107 -\n 0) Not mentioned\n 1) Mentioned\n 999) Not Applicable\n\n"
            ),
            "Coding": (
            "If Q107_1 to Q107_4 == 0 then\n"
            "0: None\n\n"
            "Count how many of Q107_1 to Q107_4 are 1.\n"
            "If count == 1 then\n"
            "1: Moderate (1 task)\n\n"
            "If count >= 2 then\n"
            "2: High (2 or more tasks)"
        ),
        }
    ]

    mapping_table = build_mapping_table(mapping_rows, title="CF B - Nursing Type Skilled Task Needs")

    # -------------------------------
    # Demographics + CF distribution (IMPUTED df)
    # -------------------------------
    # df_imp already created above and contains Nursing_Needs_Imputed
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
        source_col="Nursing_Needs_Imputed",
        out_col="Nursing_CF_Value",
        allowed_values={0, 1, 2},
    )

    nursing_matrix = build_cf_matrix_row_pct_n_table(
        df_demo=df_demo,
        cf_col="Nursing_Needs_Imputed",
        category_order=[0, 1, 2],
        category_labels={
            0: "0: None",
            1: "1: Moderate (1 task)",
            2: "2: High (2 or more tasks)",
        },
        title="Complicating Factor: Nursing Type Skilled Task Needs (%, n)",
        total_denominator=2499,  # ✅ THIS is the key
    )


    util_crosstab = build_cf_x_utilization_crosstab_table(
    df_demo=df_demo,
    cf_col="Nursing_Needs_Imputed",
    category_order=[0, 1, 2],
    category_labels={
        0: "0: None",
        1: "1: Moderate (1 task)",
        2: "2: High (2 or more tasks)",
    },
    util_qcodes=["Q78", "Q85", "Q91", "Q93", "Q96", "Q103"],
    util_question_meta=HEALTHCARE_UTILIZATION_QUESTIONS,
    title="CF B (Nursing Needs) × Healthcare Utilization (counts)",
    mode="valid",   # or "ge1"
    )

    util_binned_table = build_cf_x_utilization_binned_table(
        df_demo=df_demo,
        cf_col="Nursing_Needs_Imputed",
        category_order=[0, 1, 2],
        category_labels={
            0: "0: None",
            1: "1: Moderate (1 task)",
            2: "2: High (2 or more tasks)",
        },
        util_qcodes=["Q78", "Q85", "Q91", "Q93", "Q96", "Q103"],
        util_question_meta=HEALTHCARE_UTILIZATION_QUESTIONS,
        title="CF B (Nursing Needs) × Healthcare Utilization (0 / 1–2 / 3–5 / 6+)",
        show_pct=True,   # set False if you only want counts
    )

    util_tables = build_cf_x_utilization_binned_tables_per_question(
        df_demo=df_demo,
        cf_col="Nursing_Needs_Imputed",
        category_order=[0, 1, 2],
        category_labels={
            0: "0: None",
            1: "1: Moderate (1 task)",
            2: "2: High (2 or more tasks)",
        },
        util_qcodes=["Q78", "Q85", "Q91", "Q93", "Q96", "Q103"],
        util_question_meta=HEALTHCARE_UTILIZATION_QUESTIONS,
        title_prefix="CF B (Nursing Needs) × Healthcare Utilization (0 / 1–2 / 3–5 / 6+)",
        show_pct=True,   # or False if you want only counts
    )
    # -------------------------------
    # Healthcare utilization: cross with Nursing_Needs (0/1/2)
    # -------------------------------
    nursing_order = [0, 1, 2]
    util_figs = {}
    for qcode in HC_UTIL_QUESTIONS:
        df_demo = build_gp_visits(df_demo, source_col=qcode, out_col="GP_Visits")
        df_demo = add_visit_bins(df_demo, visits_col="GP_Visits", out_col="GP_Visits_Bin")

        meta = HEALTHCARE_UTILIZATION_QUESTIONS.get(qcode, {})
        util_title = meta.get("title", qcode)

        _, fig_util = gp_visits_by_cf_group(
            df_demo,
            cf_col="Nursing_Needs_Imputed",
            cf_order=nursing_order,
            title=f"{qcode}: {util_title} - Cross with Nursing Type Skilled Task Needs (Imputed: 999→0)",
        )

        # FIX LEGEND TITLE HERE
        fig_util.update_layout(
            legend_title_text=util_title
        )

        util_figs[qcode] = fig_util

    # -------------------------------
    # CF distribution across demographics (IMPUTED)
    # -------------------------------
    age_counts, age_fig = cf_distribution_rowwise_by_group(
        df_demo=df_demo,
        cf_col="Nursing_Needs_Imputed",
        group_col="Age_Bin",
        cf_order=[0, 1, 2],
        group_order=["<40", "40–65", "65–85", ">=85"],
        title="Nursing Needs: Age distribution within each CF level (row-wise %, n)",
        legend_title="Age Bin",
    )

    gender_counts, gender_fig = cf_distribution_rowwise_by_group(
        df_demo=df_demo,
        cf_col="Nursing_Needs_Imputed",
        group_col="Gender_Label",
        cf_order=[0, 1, 2],
        group_order=["Male", "Female"],
        title="Nursing Needs: Gender distribution within each CF level (row-wise %, n)",
        legend_title="Gender",
    )

    eth_counts, eth_fig = cf_distribution_rowwise_by_group(
        df_demo=df_demo,
        cf_col="Nursing_Needs_Imputed",
        group_col="Ethnicity_Label",
        cf_order=[0, 1, 2],
        group_order=["Chinese", "Malay", "Indian", "Others"],
        title="Nursing Needs: Ethnicity distribution within each CF level (row-wise %, n)",
        legend_title="Ethnicity",
    )



    return html.Div([
        mapping_table,
        html.Br(),
        table,
        html.Br(),
        #cards,
        html.Br(),
        html.Hr(),
        html.H4("Distribution of # of Categories - Nursing Type Skilled Task Needs"),
        html.Hr(),
        html.H4("Category Counts (without imputation)"),
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
        html.H4("Category Counts (after imputation: 999 → 0)"),
        dash_table.DataTable(
            data=count_table_imputed.to_dict("records"),
            columns=[{"name": c, "id": c} for c in count_table_imputed.columns],
            style_cell={"textAlign": "center"},
            style_header={"fontWeight": "bold"},
        ),
        html.Br(),
        html.Hr(),
        nursing_matrix,
        html.Br(),
        html.Hr(),
        util_tables,
        html.Br(),
        html.Hr(),
        html.H3("Distribution of # of CFs by Demographics (Nursing Needs)"),
        html.Hr(),
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
            dbc.CardBody(
                dcc.Graph(figure=gender_fig, config={"displayModeBar": False})
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
        html.H3("Distribution of # of CFs by Utilization (Nursing Needs)"),
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
        )

    ])
