import pandas as pd
from dash import html, dcc, dash_table
import plotly.express as px
from logic.mapping_helpers import build_mapping_table
from logic.FA_helper import binary_question_group_table, response_summary_cards
import dash_bootstrap_components as dbc
from logic.demographics_helpers import add_age_bins, add_categorical_labels
from logic.cf_distribution_helpers import build_cf_value_column, cf_distribution_by_group
from logic.utilization_helpers import build_gp_visits, add_visit_bins, gp_visits_by_cf_group

# ------------------------------------------------------------
# 1. FUNCTION: Compute Functional Assessment Category
# ------------------------------------------------------------

# Columns used (same as your dataset)
Q155_cols = ["Q155_i", "Q155_ii", "Q155_iii", "Q155_iv", "Q155_v", "Q155_vi"]
Q167_cols = ["Q167_i", "Q167_ii", "Q167_iii", "Q167_iv", "Q167_v", "Q167_vi", "Q167_vii"]
Q155_labels = ["Bathing", "Dressing", "Transferring", "Using the toilet","Continence", "Eating"]
Q167_labels = ["Handling personal finances", "Meal preparation", "Shopping", "Travelling", "Doing housework", "Using the telephone", "Taking Medications"]
HC_UTIL_QUESTIONS = ["Q78", "Q85", "Q91", "Q93", "Q96", "Q103"]

def compute_FA_category(row):
    Q155 = row[Q155_cols].values
    Q167 = row[Q167_cols].values

    ADL_all_2 = all(x == 2 for x in Q155)      # No ADL deficit
    IADL_any_1 = any(x == 1 for x in Q167)     # At least one IADL deficit
    IADL_all_2 = all(x == 2 for x in Q167)     # No IADL deficit

    # Apply our corrected logic
    if ADL_all_2 and IADL_all_2:
        return 0   # No deficit

    elif ADL_all_2 and IADL_any_1:
        return 1   # IADL deficit, no ADL deficit

    elif IADL_any_1:
        return 2   # Any ADL deficit

    return None

# ------------------------------------------------------------
# 2. FUNCTION: Add the FA column to dataframe
# ------------------------------------------------------------
def add_FA_column(df):
    df["Functional_Assessment"] = df.apply(compute_FA_category, axis=1)
    return df

# ------------------------------------------------------------
# 3. FUNCTION: Convert float
# ------------------------------------------------------------

FA_LEGEND_LABELS = {
    "0": "0: No deficit",
    "1": "1: IADL deficit only",
    "2": "2: Any ADL deficit",
    "0.0": "0: No deficit",
    "1.0": "1: IADL deficit only",
    "2.0": "2: Any ADL deficit",
}

def rename_fa_legend(fig):
    fig.for_each_trace(lambda t: t.update(name=FA_LEGEND_LABELS.get(str(t.name), t.name)))
    return fig

# ------------------------------------------------------------
# 5. FUNCTION: Page Layout
# ------------------------------------------------------------
def FA_layout(df):
    if "Functional_Assessment" not in df.columns: df = add_FA_column(df)
    q155_cards = response_summary_cards(
        df,
        cols=Q155_cols,
        title="Q155 – ADL responses")

    q167_cards = response_summary_cards(
        df,
        cols=Q167_cols,
        title="Q167 – IADL responses")

    q155_table = binary_question_group_table(
        df,
        cols=Q155_cols,
        row_labels=Q155_labels,
        code_yes=1,
        code_no=2,
        title_text=(
            "Q155 – ADL –\n"
                "Do you have any problem with any of the following:\n"
                "(i) Bathing\n"
                "(ii) Dressing\n"
                "(iii) Transferring\n"
                "(iv) Using the toilet\n"
                "(v) Continence\n"
                "(vi) Eating\n\n"
        ),
    )
    q167_table = binary_question_group_table(
        df,
        cols=Q167_cols,
        row_labels=Q167_labels,
        code_yes=1,
        code_no=2,
        title_text=(
            "Q167 – IADL –\n"
                "[For respondents age ≥ 65]\n"
                "Do you have any problem with any of the following:\n"
                "(i) Handling personal finances\n"
                "(ii) Meal preparation\n"
                "(iii) Shopping\n"
                "(iv) Travelling\n"
                "(v) Doing housework\n"
                "(vi) Using the telephone\n"
                "(vii) Taking Medications"
        ),
    )
    # Create category counts
    count_table = pd.DataFrame({
        "Category": [0, 1, 2],
        "Meaning": [
            "No deficit",
            "IADL deficit, no ADL deficit",
            "Any ADL deficit"
        ],
        "Count": [
            df["Functional_Assessment"].eq(0).sum(),
            df["Functional_Assessment"].eq(1).sum(),
            df["Functional_Assessment"].eq(2).sum()
        ]
    })

    # Create distribution bar chart
    fig = px.bar(
        count_table,
        x="Meaning",
        y="Count",
        title="Functional Assessment Distribution",
        text="Count",
        color="Category"
    )

    # Create data table for raw values
    display_cols = (
        ["Functional_Assessment"]
        + Q155_cols
        + Q167_cols
    )

    mapping_rows = [
        {
            "Complicating Factor": "A. Functional Assessment",
            "Mapped Question No from Survey": "Q155 & Q167",
            "Question Description": (
                "Q155 - ADL -\n"
                "Do you have any problem with any of the following:\n"
                "(i) Bathing\n"
                "(ii) Dressing\n"
                "(iii) Transferring\n"
                "(iv) Using the toilet\n"
                "(v) Continence\n"
                "(vi) Eating\n\n"
                "Q167 - IADL -\n"
                "[For respondents age ≥ 65]\n"
                "Do you have any problem with any of the following:\n"
                "(i) Handling personal finances\n"
                "(ii) Meal preparation\n"
                "(iii) Shopping\n"
                "(iv) Travelling\n"
                "(v) Doing housework\n"
                "(vi) Using the telephone\n"
                "(vii) Taking Medications"
            ),
            "Levels": (
                "0: No deficit\n\n"
                "1: any IADL deficit, no ADL deficit\n\n"
                "2: Any ADL deficit"),
            "Data Mapping": (
                "Q155 -\n 1) Yes\n 2) No\n 777) X (Refused)\n\n"
                "Q167 -\n 1) Yes\n 2) No\n 777) X (Refused)\n 999) Not applicable"
            ),
            "Coding": (
                "If Q155_i to Q155_vi == 2 AND\n"
                "if Q167_i to Q167_vii == 2 then\n"
                "0: No deficit\n\n"
                "If any Q167_i to Q167_vii == 1 AND\n"
                "if Q155_i to Q155_vi == 2 then\n"
                "1: any IADL deficit, no ADL deficit\n\n"
                "If Q155_i to Q155_vi == 1 then\n"
                "2: Any ADL deficit"
            ),

        }
    ]
    mapping_table = build_mapping_table(mapping_rows, title="CF A - Functional Assessment Mapping")

    # ensure Functional_Assessment exists
    if "Functional_Assessment" not in df.columns:
        df = add_FA_column(df)

    # demographics
    df_demo = add_age_bins(df, age_col="Q2", out_col="Age_Bin")
    df_demo = add_categorical_labels(
        df_demo,
        mappings={
            "Gender_Label": {"source": "Q4", "map": {1: "Male", 2: "Female"}},
            "Ethnicity_Label": {"source": "Q3", "map": {1: "Chinese", 2: "Malay", 3: "Indian", 4: "Others"}},
        },
    )

    # CF count for this CF: present if Functional_Assessment in {1,2}, absent if {0}
    # Keep original CF values (0/1/2) for grouping
    df_demo = build_cf_value_column(
        df_demo,
        source_col="Functional_Assessment",
        out_col="FA_CF_Value",
        allowed_values={0, 1, 2},  # keep only valid categories
    )

    # --- Distribution of # of CFs by demographics ---
    age_order = ["<40", "40–65", "65–85", ">=85"]
    gender_order = ["Male", "Female"]
    eth_order = ["Chinese", "Malay", "Indian", "Others"]

    age_counts, age_fig = cf_distribution_by_group(
        df_demo,
        cf_count_col="FA_CF_Value",
        group_col="Age_Bin",
        group_order=age_order,
        title="Functional Assessment: # of CFs by Age Bin",
        cf_label="CF Levels",
    )

    gender_counts, gender_fig = cf_distribution_by_group(
        df_demo,
        cf_count_col="FA_CF_Value",
        group_col="Gender_Label",
        group_order=gender_order,
        title="Functional Assessment: # of CFs by Gender",
        cf_label="CF Levels",
    )

    eth_counts, eth_fig = cf_distribution_by_group(
        df_demo,
        cf_count_col="FA_CF_Value",
        group_col="Ethnicity_Label",
        group_order=eth_order,
        title="Functional Assessment: # of CFs by Ethnicity",
        cf_label="CF Levels",
    )
    cf_distribution_by_group

    age_fig = rename_fa_legend(age_fig)
    gender_fig = rename_fa_legend(gender_fig)
    eth_fig = rename_fa_legend(eth_fig)

    # ---- Q78 (Private GP visits) cross with Functional Assessment ----
    df_demo = build_gp_visits(df_demo, source_col="Q78", out_col="GP_Visits")
    df_demo = add_visit_bins(df_demo, visits_col="GP_Visits", out_col="GP_Visits_Bin")

    fa_order = [0, 1, 2]
    gp_counts, gp_fig = gp_visits_by_cf_group(
        df_demo,
        cf_col="Functional_Assessment",
        cf_order=fa_order,
        title="Q78 (Private GP visits): Cross with Functional Assessment",
    )
    gp_fig.update_layout(legend_title_text="Private GP visits")

    # ---- Q85 (Polyclinic visits) cross with Functional Assessment ----
    df_demo = build_gp_visits(df_demo, source_col="Q85", out_col="GP_Visits")
    df_demo = add_visit_bins(df_demo, visits_col="GP_Visits", out_col="GP_Visits_Bin")

    fa_order = [0, 1, 2]
    gp_counts, polyclinic_fig = gp_visits_by_cf_group(
        df_demo,
        cf_col="Functional_Assessment",
        cf_order=fa_order,
        title="Q85 (Polyclinic Visits): Cross with Functional Assessment",
    )
    polyclinic_fig.update_layout(legend_title_text="Polyclinic visits")

    # ---- Q91 (SOC visits) cross with Functional Assessment ----
    df_demo = build_gp_visits(df_demo, source_col="Q91", out_col="GP_Visits")
    df_demo = add_visit_bins(df_demo, visits_col="GP_Visits", out_col="GP_Visits_Bin")

    fa_order = [0, 1, 2]
    gp_counts, soc_fig = gp_visits_by_cf_group(
        df_demo,
        cf_col="Functional_Assessment",
        cf_order=fa_order,
        title="Q91 (SOC Visits): Cross with Functional Assessment",
    )
    soc_fig.update_layout(legend_title_text="SOC visits")

    # ---- Q93 (ED visits) cross with Functional Assessment ----
    df_demo = build_gp_visits(df_demo, source_col="Q93", out_col="GP_Visits")
    df_demo = add_visit_bins(df_demo, visits_col="GP_Visits", out_col="GP_Visits_Bin")

    fa_order = [0, 1, 2]
    gp_counts, ed_fig = gp_visits_by_cf_group(
        df_demo,
        cf_col="Functional_Assessment",
        cf_order=fa_order,
        title="Q93 (ED Visits): Cross with Functional Assessment",
    )
    ed_fig.update_layout(legend_title_text="ED visits")

    # ---- Q96 (Public hospital visits) cross with Functional Assessment ----
    df_demo = build_gp_visits(df_demo, source_col="Q96", out_col="GP_Visits")
    df_demo = add_visit_bins(df_demo, visits_col="GP_Visits", out_col="GP_Visits_Bin")

    fa_order = [0, 1, 2]
    gp_counts, public_hospital_fig = gp_visits_by_cf_group(
        df_demo,
        cf_col="Functional_Assessment",
        cf_order=fa_order,
        title="Q96 (Public Hospital Visits): Cross with Functional Assessment",
    )
    public_hospital_fig.update_layout(legend_title_text="Public hospital visits")

    # ---- Q103 (Private hospital visits) cross with Functional Assessment ----
    df_demo = build_gp_visits(df_demo, source_col="Q103", out_col="GP_Visits")
    df_demo = add_visit_bins(df_demo, visits_col="GP_Visits", out_col="GP_Visits_Bin")

    fa_order = [0, 1, 2]
    gp_counts, private_hospital_fig = gp_visits_by_cf_group(
        df_demo,
        cf_col="Functional_Assessment",
        cf_order=fa_order,
        title="Q103 (Private Hospital Visits): Cross with Functional Assessment",
    )
    private_hospital_fig.update_layout(legend_title_text="Private hospital visits")


    return html.Div([
        mapping_table,
        dbc.Row(
            [
                dbc.Col(q155_table, width=6),
                dbc.Col(q167_table, width=6),
            ],
            className="mb-4",
        ),
        #q155_cards,
        #q167_cards,
        html.Hr(),
        html.H4("Distribution of # of Categories - Functional Assessment"),
        dash_table.DataTable(
            data=count_table.to_dict("records"),
            columns=[{"name": i, "id": i} for i in count_table.columns],
            style_cell={"textAlign": "center"},
            style_header={"fontWeight": "bold"},
        ),
        html.Br(),
        #html.H4("Distribution Chart"),
        #dcc.Graph(figure=fig),
        html.Br(),
        html.Hr(),
        html.H3("Distribution of # of CFs by Demographics (Functional Assessment)"),
        html.Hr(),
        dbc.Card(
            dbc.CardBody(
                dcc.Graph(
                    figure=age_fig,
                    config={"displayModeBar": False},
                )
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
                dcc.Graph(
                    figure=gender_fig,
                    config={"displayModeBar": False},
                )
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
                dcc.Graph(
                    figure=eth_fig,
                    config={"displayModeBar": False},
                )
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
        html.H3("Distribution of # of CFs by Utilization (Functional Assessment)"),
        html.Hr(),
        dbc.Card(
            dbc.CardBody(
                dcc.Graph(
                    figure=gp_fig,
                    config={"displayModeBar": False},
                )
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
        dbc.Card(
            dbc.CardBody(
                dcc.Graph(
                    figure=polyclinic_fig,
                    config={"displayModeBar": False},
                )
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
        dbc.Card(
            dbc.CardBody(
                dcc.Graph(
                    figure=soc_fig,
                    config={"displayModeBar": False},
                )
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
        dbc.Card(
            dbc.CardBody(
                dcc.Graph(
                    figure=ed_fig,
                    config={"displayModeBar": False},
                )
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
        dbc.Card(
            dbc.CardBody(
                dcc.Graph(
                    figure=public_hospital_fig,
                    config={"displayModeBar": False},
                )
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
        dbc.Card(
            dbc.CardBody(
                dcc.Graph(
                    figure=private_hospital_fig,
                    config={"displayModeBar": False},
                )
            ),
            style={
                "borderRadius": "16px",
                "boxShadow": "0 6px 18px rgba(0,0,0,0.08)",
                "border": "1px solid rgba(0,0,0,0.06)",
                "backgroundColor": "white",
                "padding": "6px",
            },
        ),
        html.Hr()
    ])
