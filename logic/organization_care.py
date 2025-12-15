import pandas as pd
from dash import html, dcc, dash_table
import plotly.express as px
import dash_bootstrap_components as dbc

from logic.mapping_helpers import build_mapping_table
from logic.demographics_helpers import add_age_bins, add_categorical_labels
from logic.cf_distribution_helpers import build_cf_value_column, cf_distribution_by_group
from logic.utilization_helpers import build_gp_visits, add_visit_bins, gp_visits_by_cf_group
from logic.question_texts import HEALTHCARE_UTILIZATION_QUESTIONS


# ------------------------------------------------------------
# Inputs
# ------------------------------------------------------------
GP_COL  = "Q80"   # GP visits
PC_COL  = "Q85"   # PC visits
SOC_COL = "Q91"   # SOC visits

HC_UTIL_QUESTIONS = ["Q78", "Q85", "Q91", "Q93", "Q96", "Q103"]


# ------------------------------------------------------------
# Core CF Logic
# ------------------------------------------------------------
def _clean(v):
    if v is None or pd.isna(v) or v in (777, 888, 999):
        return 0
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def compute_organization_of_care(row):
    """
    CF: Organization of Care

    0 = ≤1 doctor, 1 site
    1 = >1 doctor, 1 site
    2 = >1 doctor, >1 site
    """

    gp  = 1 if _clean(row.get(GP_COL))  >= 1 else 0
    pc  = 1 if _clean(row.get(PC_COL))  >= 1 else 0
    soc = 1 if _clean(row.get(SOC_COL)) >= 1 else 0

    # Category 0
    if (gp, pc, soc) in [(0,0,0), (1,0,0), (0,0,1)]:
        return 0

    # Category 1
    if (gp, pc, soc) == (0,1,0):
        return 1

    # Category 2
    return 2


def add_organization_of_care_column(df):
    df = df.copy()
    df["Organization_of_Care_CF"] = df.apply(
        compute_organization_of_care, axis=1
    )
    return df


# ------------------------------------------------------------
# Dash Layout
# ------------------------------------------------------------
def OrganizationOfCare_layout(df):

    # ----------------------------------------
    # Compute CF
    # ----------------------------------------
    df = add_organization_of_care_column(df)

    # ----------------------------------------
    # Mapping table
    # ----------------------------------------
    mapping_rows = [
        {
            "Complicating Factor": "D. Organization of Care",
            "Mapped Question No from Survey": "Q80, Q85, Q91",
            "Question Description": (
                "Q80 – GP visits\n"
                "Q85 – PC visits\n"
                "Q91 – SOC visits"
            ),
            "Levels": (
                "0 = patient will see no more than 1 doctor, from 1 site of care\n\n"
                "1 = patient will see more than 1 doctor, from 1 site of care\n\n"
                "2 = patient will see more than 1 doctor, from more than 1 site of care"
            ),
            "Data Mapping": (
                "Visits ≥ 1 are counted as presence of care\n"
                "777 / 888 / 999 treated as 0"
            ),
            "Coding": (
                "If (GP, PC, SOC) ∈ {(0,0,0), (1,0,0), (0,0,1)} → 0\n\n"
                "If (GP, PC, SOC) = (0,1,0) → 1\n\n"
                "Else → 2"
            ),
        }
    ]

    mapping_table = build_mapping_table(
        mapping_rows,
        title="CF D – Organization of Care"
    )

    # ----------------------------------------
    # Category counts
    # ----------------------------------------
    count_table = pd.DataFrame({
        "Category": [0, 1, 2],
        "Meaning": [
            "≤1 doctor, 1 site",
            ">1 doctor, 1 site",
            ">1 doctor, >1 site"
        ],
        "Count": [
            df["Organization_of_Care_CF"].eq(0).sum(),
            df["Organization_of_Care_CF"].eq(1).sum(),
            df["Organization_of_Care_CF"].eq(2).sum(),
        ]
    })

    # ----------------------------------------
    # Demographics (Age / Gender / Ethnicity)
    # ----------------------------------------
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
        source_col="Organization_of_Care_CF",
        out_col="OrgCare_CF_Value",
        allowed_values={0, 1, 2},
    )

    age_counts, age_fig = cf_distribution_by_group(
        df_demo,
        cf_count_col="OrgCare_CF_Value",
        group_col="Age_Bin",
        group_order=["<40", "40–65", "65–85", ">=85"],
        title="Organization of Care: Distribution by Age",
        cf_label="Organization of Care Level",
    )

    gender_counts, gender_fig = cf_distribution_by_group(
        df_demo,
        cf_count_col="OrgCare_CF_Value",
        group_col="Gender_Label",
        group_order=["Male", "Female"],
        title="Organization of Care: Distribution by Gender",
        cf_label="Organization of Care Level",
    )

    eth_counts, eth_fig = cf_distribution_by_group(
        df_demo,
        cf_count_col="OrgCare_CF_Value",
        group_col="Ethnicity_Label",
        group_order=["Chinese", "Malay", "Indian", "Others"],
        title="Organization of Care: Distribution by Ethnicity",
        cf_label="Organization of Care Level",
    )

    # ----------------------------------------
    # Healthcare utilization cross (Q78–Q103)
    # ----------------------------------------
    org_order = [0, 1, 2]
    util_figs = {}

    for qcode in HC_UTIL_QUESTIONS:
        df_demo = build_gp_visits(df_demo, source_col=qcode, out_col="GP_Visits")
        df_demo = add_visit_bins(df_demo, visits_col="GP_Visits", out_col="GP_Visits_Bin")

        meta = HEALTHCARE_UTILIZATION_QUESTIONS.get(qcode, {})
        util_title = meta.get("title", qcode)

        _, fig_util = gp_visits_by_cf_group(
            df_demo,
            cf_col="Organization_of_Care_CF",
            cf_order=org_order,
            title=f"{qcode}: {util_title} – Cross with Organization of Care",
        )

        util_figs[qcode] = fig_util

    # ----------------------------------------
    # Layout
    # ----------------------------------------
    return html.Div([
        mapping_table,
        html.Br(),

        html.H4("Category Counts"),
        dash_table.DataTable(
            data=count_table.to_dict("records"),
            columns=[{"name": c, "id": c} for c in count_table.columns],
            style_cell={"textAlign": "center"},
            style_header={"fontWeight": "bold"},
        ),

        html.Hr(),
        html.H3("Distribution of CF by Demographics"),
        dbc.Card(dbc.CardBody(dcc.Graph(figure=age_fig, config={"displayModeBar": False}))),
        html.Br(),
        dbc.Card(dbc.CardBody(dcc.Graph(figure=gender_fig, config={"displayModeBar": False}))),
        html.Br(),
        dbc.Card(dbc.CardBody(dcc.Graph(figure=eth_fig, config={"displayModeBar": False}))),

        html.Hr(),
        html.H3("Distribution of CF by Utilization"),
        html.Hr(),
        dcc.Graph(figure=util_figs["Q78"]),
        dcc.Graph(figure=util_figs["Q85"]),
        dcc.Graph(figure=util_figs["Q91"]),
        dcc.Graph(figure=util_figs["Q93"]),
        dcc.Graph(figure=util_figs["Q96"]),
        dcc.Graph(figure=util_figs["Q103"]),
    ])
