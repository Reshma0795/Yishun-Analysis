import pandas as pd
from dash import html, dcc, dash_table
import plotly.express as px
from logic.activation_helper import binary_question_group_table
from logic.mapping_helpers import build_mapping_table
import dash_bootstrap_components as dbc
from logic.demographics_helpers import add_age_bins, add_categorical_labels
from logic.cf_distribution_helpers import build_cf_value_column, cf_distribution_by_group
from logic.utilization_helpers import build_gp_visits, add_visit_bins, gp_visits_by_cf_group
from logic.question_texts import HEALTHCARE_UTILIZATION_QUESTIONS


# --------------------------------------------
# Columns for Activation in Own Care
# --------------------------------------------
ACTIVATION_COLS = ["Q64", "Q65", "Q66", "Q67", "Q68","Q69", "Q70"]
HC_UTIL_QUESTIONS = ["Q78", "Q85", "Q91", "Q93", "Q96", "Q103"]

# --------------------------------------------
# Compute Activation Category
# --------------------------------------------
def compute_activation_category(row):
    """
    Compute 'Activation in own care' category based on Q64–Q73.

    0 = mean > 3.5
    1 = 2.5 <= mean <= 3.5
    2 = mean < 2.5
    """
    values = [row[col] for col in ACTIVATION_COLS]

    # Keep only valid Likert responses (0–4)
    valid = [x for x in values if x in (0, 1, 2, 3, 4)]

    # If no valid data (all 777/999/missing), do not score
    if len(valid) == 0:
        return None

    mean_score = sum(valid) / len(valid)

    if mean_score > 3.5:
        return 0  # ready, understands, active cooperation
    elif 2.5 <= mean_score <= 3.5:
        return 1  # unsure but willing to cooperate
    else:  # mean_score < 2.5
        return 2  # major disconnect / no insight


# --------------------------------------------
# Add Activation Column to Dataset
# --------------------------------------------
def add_activation_column(df):
    df["Activation_Care"] = df.apply(compute_activation_category, axis=1)
    return df


# --------------------------------------------
# Layout Page for Dash
# --------------------------------------------
def Activation_layout(df):

    Q64_70_table = binary_question_group_table(
        df,
        cols=ACTIVATION_COLS,
        row_labels=[
            "Q64. Even when life is stressful, I know I can continue to do the things that keep me healthy",
            "Q65. I feel comfortable talking to my doctor about my health",
            "Q66. When I work to improve my health, I succeed",
            "Q67. I have brought my own information about my health to show my doctor",
            "Q68. I can stick with plans to exercise and eat a healthy diet",
            "Q69. I have lots of experience using the health care system",
            "Q70. I handle my health well"
        ],
        code_stronglyDisagree=0,
        code_Disagree=1,
        code_Neither=2,
        code_Agree=3,
        code_StronglyAgree=4,
        title_text=None,
    )

    # Category counts
    count_table = pd.DataFrame({
        "Category": [0, 1, 2],
        "Meaning": [
            "0 = Ready, understands, interested; active cooperation",
            "1 = Unsure but willing to cooperate",
            "2 = Major disconnect / no insight"
        ],
        "Count": [
            df["Activation_Care"].eq(0).sum(),
            df["Activation_Care"].eq(1).sum(),
            df["Activation_Care"].eq(2).sum(),
        ]
    })

    # Bar chart
    fig = px.bar(
        count_table,
        x="Meaning",
        y="Count",
        title="Activation in Own Care – Distribution",
        text="Count",
        color="Category"
    )

    mapping_rows = [
        {
            "Complicating Factor": "E. Activation in Own Care",
            "Mapped Question No from Survey": "Q64–Q70",
            "Question Description": (
            "Interviewer: Now I will read to you some statements. On a scale from "
            "1 – Strongly Disagree to 5 – Strongly Agree, please choose how much "
            "you agree/disagree with each statement that describes your engagement "
            "in your own health.\n"
            "1) Strongly Disagree\n"  
            "2) Disagree\n"
            "3) Neither\n"
            "4) Agree\n"
            "5) Strongly Agree\n\n"
            "Q64. Even when life is stressful, I know I can continue to do the "
            "things that keep me healthy\n\n"
            "Q65. I feel comfortable talking to my doctor about my health\n\n"
            "Q66. When I work to improve my health, I succeed\n\n"
            "Q67. I have brought my own information about my health to show my doctor\n\n"
            "Q68. I can stick with plans to exercise and eat a healthy diet\n\n"
            "Q69. I have lots of experience using the health care system\n\n"
            "Q70. I handle my health well"
        ),
            "Levels": (
                "0: ready, understands and interested in treatment; active cooperation and participative\n\n"
                "1: unsure but willing to cooperate, can be expected to provide at least a moderate level of self-care\n\n"
                "2: major disconnect, unaware/ no insight, may be defiant and can't be expected to provide even a modest level of self-care"),
            "Data Mapping": (
                "Q64–Q70 –\n"
                " 0) Strongly disagree\n"
                " 1) Disagree\n"
                " 2) Neither\n"
                " 3) Agree\n"
                " 4) Strongly agree\n"
                " 777) Refused\n"
                " 999) Not Applicable\n"
            ),
            "Coding": (
                "If mean(Q64–Q70) > 3.5 then\n"
                "0: ready, understands and interested in treatment; active cooperation "
                "and participative\n\n"
                "If 2.5 ≤ mean(Q64–Q70) ≤ 3.5 then\n"
                "1: unsure but willing to cooperate, can be expected to provide at least "
                "a moderate level of self-care\n\n"
                "If mean(Q64–Q70) < 2.5 then\n"
                "2: major disconnect, unaware/ no insight, may be defiant and can't be "
                "expected to provide even a modest level of self-care"
            ),
        }
    ]

    mapping_table = build_mapping_table(mapping_rows, title="CF E - Activation in Own Care")

        # ------------------------------------------------------------
    # Demographics + CF distribution (Activation_Care 0/1/2)
    # ------------------------------------------------------------
    if "Activation_Care" not in df.columns:
        df = add_activation_column(df)

    df_demo = add_age_bins(df, age_col="Q2", out_col="Age_Bin")

    df_demo = add_categorical_labels(
        df_demo,
        mappings={
            "Gender_Label": {"source": "Q4", "map": {1: "Male", 2: "Female"}},
            "Ethnicity_Label": {"source": "Q3", "map": {1: "Chinese", 2: "Malay", 3: "Indian", 4: "Others"}},
        },
    )

    # Keep CF levels 0/1/2 for grouping
    df_demo = build_cf_value_column(
        df_demo,
        source_col="Activation_Care",
        out_col="Activation_CF_Value",
        allowed_values={0, 1, 2},
    )

    age_order = ["<40", "40–65", "65–85", ">=85"]
    gender_order = ["Male", "Female"]
    eth_order = ["Chinese", "Malay", "Indian", "Others"]

    age_counts, age_fig = cf_distribution_by_group(
        df_demo,
        cf_count_col="Activation_CF_Value",
        group_col="Age_Bin",
        group_order=age_order,
        title="Activation in Own Care: Distribution by Age Bin (0/1/2)",
        cf_label="Activation CF Level",
    )

    gender_counts, gender_fig = cf_distribution_by_group(
        df_demo,
        cf_count_col="Activation_CF_Value",
        group_col="Gender_Label",
        group_order=gender_order,
        title="Activation in Own Care: Distribution by Gender (0/1/2)",
        cf_label="Activation CF Level",
    )

    eth_counts, eth_fig = cf_distribution_by_group(
        df_demo,
        cf_count_col="Activation_CF_Value",
        group_col="Ethnicity_Label",
        group_order=eth_order,
        title="Activation in Own Care: Distribution by Ethnicity (0/1/2)",
        cf_label="Activation CF Level",
    )

    # ------------------------------------------------------------
    # Healthcare utilization: cross with Activation_Care (0/1/2)
    # ------------------------------------------------------------
    activation_order = [0, 1, 2]
    util_figs = {}

    for qcode in HC_UTIL_QUESTIONS:
        df_demo = build_gp_visits(df_demo, source_col=qcode, out_col="GP_Visits")
        df_demo = add_visit_bins(df_demo, visits_col="GP_Visits", out_col="GP_Visits_Bin")
        meta = HEALTHCARE_UTILIZATION_QUESTIONS.get(qcode, {})
        util_title = meta.get("title", qcode)
        _, fig_util = gp_visits_by_cf_group(
            df_demo,
            cf_col="Activation_Care",
            cf_order=activation_order,
            title=f"{qcode}: {util_title} - Cross with Activation in Own Care",
        )

        util_figs[qcode] = fig_util


    return html.Div([
        mapping_table,
        html.Br(),
        Q64_70_table,
        html.Br(),
        html.Hr(),
        html.H4("Distribution of # of Categories - Activation in Own Care"),
        html.Hr(),
        html.Br(),
        dash_table.DataTable(
            data=count_table.to_dict("records"),
            columns=[{"name": c, "id": c} for c in count_table.columns],
            style_cell={"textAlign": "center"},
            style_header={"fontWeight": "bold"},
        ),
        #html.H4("Distribution Chart"),
        #dcc.Graph(figure=fig),
        html.Hr(),
        html.H3("Distribution of # of CFs by Demographics (Activation in Own Care)"),
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
        html.H3("Distribution of # of CFs by Utilization (Activation in Own Care)"),
        html.Hr(),
        dcc.Graph(figure=util_figs["Q78"]),
        dcc.Graph(figure=util_figs["Q85"]),
        dcc.Graph(figure=util_figs["Q91"]),
        dcc.Graph(figure=util_figs["Q93"]),
        dcc.Graph(figure=util_figs["Q96"]),
        dcc.Graph(figure=util_figs["Q103"]),


        html.Br()
    ])
