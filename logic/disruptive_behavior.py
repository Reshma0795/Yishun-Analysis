import pandas as pd
from dash import html, dcc, dash_table
import plotly.express as px
from logic.functional_assessment import HC_UTIL_QUESTIONS
from logic.mapping_helpers import build_mapping_table
from logic.disruptive_helper import disruptive_value_counts_table
from logic.demographics_helpers import add_age_bins, add_categorical_labels
from logic.cf_distribution_helpers import build_cf_value_column, cf_distribution_by_group
from logic.utilization_helpers import build_gp_visits, add_visit_bins, gp_visits_by_cf_group
from logic.question_texts import HEALTHCARE_UTILIZATION_QUESTIONS
import dash_bootstrap_components as dbc
# --------------------------------------------
# Columns for Disruptive Behavioural Issues
# --------------------------------------------
DISRUPTIVE_COLS = [f"Q{i}" for i in range(16, 27)]  # Q16 to Q26


# --------------------------------------------
# Compute Disruptive Behaviour CF
# --------------------------------------------
def compute_disruptive_category(row):
    """
    Disruptive behavioural issues CF based on Q16–Q26.

    Dataset:
      1 = Pass
      2 = Fail
      777 = X
      999 = Not Applicable

    Logic:
      Pass -> 1
      Fail -> 0
      Ignore 777 / 999

      Let S = sum(Pass values)

      If S >= 9 -> CF = 0
      Else if S >= 7 -> CF = 1
      Else -> CF = 2
    """

    pass_values = []

    for col in DISRUPTIVE_COLS:
        v = row[col]

        if v == 1:        # Pass
            pass_values.append(1)
        elif v == 2:      # Fail
            pass_values.append(0)
        # 777 / 999 / NaN are ignored

    # If no valid answers at all
    if len(pass_values) == 0:
        return None

    pass_count = sum(pass_values)

    if pass_count >= 9:
        return 0   # none
    elif pass_count >= 7:
        return 1   # 1 or more, not significantly affecting care
    else:
        return 2   # 1 or more, significantly affecting care

# --------------------------------------------
# Add column to dataframe
# --------------------------------------------
def add_disruptive_column(df):
    df["Disruptive_Behaviour"] = df.apply(compute_disruptive_category, axis=1)
    return df


# --------------------------------------------
# Layout for Dash page
# --------------------------------------------
def Disruptive_layout(df):

    count_table = pd.DataFrame({
        "Category": [0, 1, 2],
        "Meaning": [
            "0 = none",
            "1 = 1 or more, not significantly affecting care",
            "2 = 1 or more, significantly affecting care"
        ],
        "Count": [
            df["Disruptive_Behaviour"].eq(0).sum(),
            df["Disruptive_Behaviour"].eq(1).sum(),
            df["Disruptive_Behaviour"].eq(2).sum(),
        ]
    })

    # Bar chart
    fig = px.bar(
        count_table,
        x="Meaning",
        y="Count",
        title="Disruptive Behavioural Issues – Distribution",
        text="Count",
        color="Category"
    )

    mapping_rows = [
    {
        "Complicating Factor": "F. Disruptive behavioural issues",
        "Mapped Question No from Survey": "Q16–Q26",
        "Question Description": (
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
            "    What is his/her job?\n"
            "25. Count backwards from 20 to 1\n"
            "26. Please recall the memory phrase"
        ),
        "Levels": (
            "0 = none\n\n"
            "1 = 1 or more, not significantly affecting care\n\n"
            "2 = 1 or more, significantly affecting care"
        ),
        "Data Mapping": (
            "Q16–Q26 –\n"
            " 1) Pass (map this to 1)\n"
            " 2) Fail (map this to 0)\n"
            " 777) X (map this to 0)\n"
            " 999) Not Applicable"
        ),
        "Coding": (
            "If sum(mapped value of Q16–Q26) ≥ 9 then\n"
            "0: none\n\n"
            "Else if sum(mapped value of Q16–Q26) ≥ 7 then\n"
            "1: 1 or more, not significantly affecting care\n\n"
            "Else if sum(mapped value of Q16–Q26) < 7 then\n"
            "2: 1 or more, significantly affecting care"
        ),
    }
]

    mapping_table = build_mapping_table(mapping_rows, title="CF F - Disruptive behavioural issues")
    value_counts_table = disruptive_value_counts_table(
        df,
        cols=DISRUPTIVE_COLS,
        row_labels=[
            "Q16 – Month",
            "Q17 – Year",
            "Q18 – Time (within 1 hour)",
            "Q19 – Age",
            "Q20 – Date of birth",
            "Q21 – Home address",
            "Q22 – Where are we now?",
            "Q23 – Prime Minister",
            "Q24 – Recognition of 2 persons (job)",
            "Q25 – Count backwards 20 to 1",
            "Q26 – Recall the memory phrase",
        ],
        title_text="Value Counts for Q16–Q26 (1=Pass, 2=Fail, 777=X, 999=Not Applicable)",
    )
    # -------------------------------
    # Demographics distribution
    # -------------------------------
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
        source_col="Disruptive_Behaviour",
        out_col="Disruptive_CF_Value",
        allowed_values={0, 1, 2},
    )

    age_order = ["<40", "40–65", "65–85", ">=85"]
    gender_order = ["Male", "Female"]
    eth_order = ["Chinese", "Malay", "Indian", "Others"]

    age_counts, age_fig = cf_distribution_by_group(
        df_demo,
        cf_count_col="Disruptive_CF_Value",
        group_col="Age_Bin",
        group_order=age_order,
        title="Disruptive Behaviour: Distribution by Age Bin",
        cf_label="Disruptive Behaviour CF Level",
    )

    gender_counts, gender_fig = cf_distribution_by_group(
        df_demo,
        cf_count_col="Disruptive_CF_Value",
        group_col="Gender_Label",
        group_order=gender_order,
        title="Disruptive Behaviour: Distribution by Gender",
        cf_label="Disruptive Behaviour CF Level",
    )

    eth_counts, eth_fig = cf_distribution_by_group(
        df_demo,
        cf_count_col="Disruptive_CF_Value",
        group_col="Ethnicity_Label",
        group_order=eth_order,
        title="Disruptive Behaviour: Distribution by Ethnicity",
        cf_label="Disruptive Behaviour CF Level",
    )
    # -------------------------------
    # Healthcare utilization cross
    # -------------------------------
    disruptive_order = [0, 1, 2]
    util_figs = {}

    for qcode in HC_UTIL_QUESTIONS:
        df_demo = build_gp_visits(df_demo, source_col=qcode, out_col="GP_Visits")
        df_demo = add_visit_bins(df_demo, visits_col="GP_Visits", out_col="GP_Visits_Bin")

        meta = HEALTHCARE_UTILIZATION_QUESTIONS.get(qcode, {})
        util_title = meta.get("title", qcode)

        _, fig_util = gp_visits_by_cf_group(
            df_demo,
            cf_col="Disruptive_Behaviour",
            cf_order=disruptive_order,
            title=f"{qcode}: {util_title} - Cross with Disruptive Behavioural Issues",
        )
        util_figs[qcode] = fig_util


    return html.Div([
        mapping_table,
        html.Br(),
        html.H3("Disruptive Behavioural Issues – Computed Complicating Factor"),
        value_counts_table,
        html.Br(),
        dash_table.DataTable(
            data=count_table.to_dict("records"),
            columns=[{"name": c, "id": c} for c in count_table.columns],
            style_cell={"textAlign": "center"},
            style_header={"fontWeight": "bold"},
        ),

        html.Hr(),
        html.H3("Distribution of # of CFs by Demographics - Disruptive Behavioural Issues"),
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
        html.H3("Distribution of # of CFs by Utilization - Disruptive Behavioural Issues"),
        html.Hr(),

        dcc.Graph(figure=util_figs["Q78"]),
        dcc.Graph(figure=util_figs["Q85"]),
        dcc.Graph(figure=util_figs["Q91"]),
        dcc.Graph(figure=util_figs["Q93"]),
        dcc.Graph(figure=util_figs["Q96"]),
        dcc.Graph(figure=util_figs["Q103"]),


        #html.H4("Distribution Chart"),
        #dcc.Graph(figure=fig),

        html.Br()
    ])
