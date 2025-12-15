import pandas as pd
from dash import html, dcc, dash_table
import plotly.express as px
import dash_bootstrap_components as dbc

from logic.question_texts import HEALTHCARE_UTILIZATION_QUESTIONS
from logic.mapping_helpers import build_mapping_table
from logic.value_counts_helpers import build_value_counts_table

from logic.demographics_helpers import add_age_bins, add_categorical_labels
from logic.cf_distribution_helpers import build_cf_value_column, cf_distribution_by_group
from logic.utilization_helpers import build_gp_visits, add_visit_bins, gp_visits_by_cf_group

# --------------------------------------------
# Column name
# --------------------------------------------
POLY_COL = "Q132"
HC_UTIL_QUESTIONS = ["Q78", "Q85", "Q91", "Q93", "Q96", "Q103"]
# --------------------------------------------
# Compute Polypharmacy CF
# --------------------------------------------
def compute_polypharmacy_category(row):
    """
    Compute 'Polypharmacy' CF based on Q132.

    Mapping:
        If Q132 < 5         → 0 = fewer than 5 prescription medications
        If 5 <= Q132 <= 8   → 1 = 5 to 8 prescription medications
        If Q132 >= 9        → 2 = 9 or more prescription medications
        If Q132 in {777,999} or missing → None (not scored)
    """
    val = row[POLY_COL]

    if pd.isna(val):
        return None

    try:
        v = int(val)
    except (TypeError, ValueError):
        return None

    if v in (777, 999):
        return None

    if v < 5:
        return 0
    elif 5 <= v <= 8:
        return 1
    elif v >= 9:
        return 2

    # fallback
    return None


# --------------------------------------------
# Add column to dataframe
# --------------------------------------------
def add_polypharmacy_column(df):
    df["Polypharmacy_CF"] = df.apply(compute_polypharmacy_category, axis=1)
    return df

def add_polypharmacy_column_imputed(df):
    """
    Creates an imputed version of Polypharmacy_CF where:
    Q132: 777 / 999 → 0
    Then recomputes Polypharmacy_CF using the SAME logic.
    """
    df_imp = df.copy()

    if POLY_COL in df_imp.columns:
        df_imp[POLY_COL] = pd.to_numeric(df_imp[POLY_COL], errors="coerce")
        df_imp[POLY_COL] = df_imp[POLY_COL].replace({777: 0, 999: 0})

    df_imp["Polypharmacy_CF_Imputed"] = df_imp.apply(
        compute_polypharmacy_category, axis=1
    )
    return df_imp

# --------------------------------------------
# Layout for Dash page
# --------------------------------------------
def Polypharmacy_layout(df):

    # ensure CF exists
    df = add_polypharmacy_column(df)

    # -----------------------
    # Mapping table
    # -----------------------
    mapping_rows = [
        {
            "Complicating Factor": "I. Polypharmacy",
            "Mapped Question No from Survey": "Q132",
            "Question Description": (
                "Q132. How many types of long term medications do you take regularly?\n"
                "Include all medications prescribed by medical professionals."
            ),
            "Levels": (
                "0 = fewer than 5 prescription medications\n\n"
                "1 = 5 to 8 prescription medications\n\n"
                "2 = 9 or more prescription medications"
            ),
            "Data Mapping": (
                "Q132 –\n"
                " 777) X (Refused)\n"
                " 999) Not Applicable"
            ),
            "Coding": (
                "If Q132 < 5 then\n"
                "0: fewer than 5 prescription medications\n\n"
                "If 5 ≤ Q132 ≤ 8 then\n"
                "1: 5 to 8 prescription medications\n\n"
                "If Q132 ≥ 9 then\n"
                "2: 9 or more prescription medications"
            ),
        }
    ]
    mapping_table = build_mapping_table(mapping_rows, title="CF I - Polypharmacy")

    # -----------------------
    # ✅ Value counts table (Q132)
    # -----------------------
    vc_df = build_value_counts_table(
        df,
        POLY_COL,
        include_missing=True,
        sort_numeric=True,
        missing_label="Missing",
    )

    # Optional bar chart (counts)
    vc_fig = px.bar(
        vc_df,
        x="Response",
        y="Count",
        text="Count",
        title="Q132 – Value Counts",
    )
    vc_fig.update_traces(textposition="outside")
    vc_fig.update_layout(
        margin=dict(l=10, r=10, t=50, b=10),
        xaxis_title="Response",
        yaxis_title="Count",
    )

    # -----------------------
    # Category counts (0/1/2)
    # -----------------------
    # WITHOUT IMPUTATION
    # -----------------------
    count_table = pd.DataFrame({
        "Category": [0, 1, 2],
        "Meaning": [
            "0 = fewer than 5 prescription medications",
            "1 = 5 to 8 prescription medications",
            "2 = 9 or more prescription medications"
        ],
        "Count": [
            df["Polypharmacy_CF"].eq(0).sum(),
            df["Polypharmacy_CF"].eq(1).sum(),
            df["Polypharmacy_CF"].eq(2).sum(),
        ]
    })

    # -----------------------
    # AFTER IMPUTATION (777/999 → 0)
    # -----------------------
    df_imp = add_polypharmacy_column_imputed(df)

    count_table_imputed = pd.DataFrame({
        "Category": [0, 1, 2],
        "Meaning": [
            "0 = fewer than 5 prescription medications",
            "1 = 5 to 8 prescription medications",
            "2 = 9 or more prescription medications"
        ],
        "Count": [
            df_imp["Polypharmacy_CF_Imputed"].eq(0).sum(),
            df_imp["Polypharmacy_CF_Imputed"].eq(1).sum(),
            df_imp["Polypharmacy_CF_Imputed"].eq(2).sum(),
        ]
    })


    # -----------------------
    # Demographics + CF distribution (0/1/2)
    # -----------------------
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
        source_col="Polypharmacy_CF_Imputed",
        out_col="Polypharmacy_CF_Value",
        allowed_values={0, 1, 2},
    )


    age_order = ["<40", "40–65", "65–85", ">=85"]
    gender_order = ["Male", "Female"]
    eth_order = ["Chinese", "Malay", "Indian", "Others"]

    age_counts, age_fig = cf_distribution_by_group(
    df_demo,
    cf_count_col="Polypharmacy_CF_Value",
    group_col="Age_Bin",
    group_order=["<40", "40–65", "65–85", ">=85"],
    title="Polypharmacy (Imputed): Distribution by Age",
    cf_label="Polypharmacy CF Level",
    )

    gender_counts, gender_fig = cf_distribution_by_group(
        df_demo,
        cf_count_col="Polypharmacy_CF_Value",
        group_col="Gender_Label",
        group_order=["Male", "Female"],
        title="Polypharmacy (Imputed): Distribution by Gender",
        cf_label="Polypharmacy CF Level",
    )

    eth_counts, eth_fig = cf_distribution_by_group(
        df_demo,
        cf_count_col="Polypharmacy_CF_Value",
        group_col="Ethnicity_Label",
        group_order=["Chinese", "Malay", "Indian", "Others"],
        title="Polypharmacy (Imputed): Distribution by Ethnicity",
        cf_label="Polypharmacy CF Level",
    )


    # -----------------------
    # Healthcare utilization cross (Q78..Q103) vs Polypharmacy_CF (0/1/2)
    # -----------------------
    poly_order = [0, 1, 2]
    util_figs = {}

    for qcode in HC_UTIL_QUESTIONS:
        df_demo = build_gp_visits(df_demo, source_col=qcode, out_col="GP_Visits")
        df_demo = add_visit_bins(df_demo, visits_col="GP_Visits", out_col="GP_Visits_Bin")
        meta = HEALTHCARE_UTILIZATION_QUESTIONS.get(qcode, {})
        util_title = meta.get("title", qcode)
        _, fig_util = gp_visits_by_cf_group(
            df_demo,
            cf_col="Polypharmacy_CF_Imputed",
            cf_order=poly_order,
            title=f"{qcode}: {util_title} - Cross with Polypharmacy (Imputed: 777/999 → 0)",
        )

        util_figs[qcode] = fig_util


    # -----------------------
    # Layout
    # -----------------------
    return html.Div([
        mapping_table,
        html.Br(),
        html.H4("Q132 – Value Counts"),
        dash_table.DataTable(
            data=vc_df.to_dict("records"),
            columns=[{"name": c, "id": c} for c in vc_df.columns],
            style_cell={"textAlign": "left", "padding": "10px"},
            style_header={"fontWeight": "bold", "backgroundColor": "#5b3fd3", "color": "white"},
            style_table={"borderRadius": "12px", "overflow": "hidden"},
        ),
        html.Br(),
        html.Hr(),
        html.H4("Distribution of # of Categories - Polypharmacy"),
        html.Hr(),
        html.H4("Category Counts (without imputation)"),
        dash_table.DataTable(
            data=count_table.to_dict("records"),
            columns=[{"name": c, "id": c} for c in count_table.columns],
            style_cell={"textAlign": "center"},
            style_header={"fontWeight": "bold"},
        ),
        html.Br(),
        html.Hr(),
        html.H4("Category Counts (after imputation: 777/999 → 0)"),
        dash_table.DataTable(
            data=count_table_imputed.to_dict("records"),
            columns=[{"name": c, "id": c} for c in count_table_imputed.columns],
            style_cell={"textAlign": "center"},
            style_header={"fontWeight": "bold"},
        ),
        html.Hr(),
        html.H3("Distribution of # of CFs by Demographics - Polypharmacy"),
        html.Hr(),
        dbc.Card(
            dbc.CardBody(dcc.Graph(figure=age_fig, config={"displayModeBar": False})),
            style={"borderRadius": "16px", "boxShadow": "0 6px 18px rgba(0,0,0,0.08)",
                   "border": "1px solid rgba(0,0,0,0.06)", "backgroundColor": "white", "padding": "6px"},
        ),
        html.Br(),
        dbc.Card(
            dbc.CardBody(dcc.Graph(figure=gender_fig, config={"displayModeBar": False})),
            style={"borderRadius": "16px", "boxShadow": "0 6px 18px rgba(0,0,0,0.08)",
                   "border": "1px solid rgba(0,0,0,0.06)", "backgroundColor": "white", "padding": "6px"},
        ),
        html.Br(),
        dbc.Card(
            dbc.CardBody(dcc.Graph(figure=eth_fig, config={"displayModeBar": False})),
            style={"borderRadius": "16px", "boxShadow": "0 6px 18px rgba(0,0,0,0.08)",
                   "border": "1px solid rgba(0,0,0,0.06)", "backgroundColor": "white", "padding": "6px"},
        ),
        html.Br(),
        html.Hr(),
        html.H3("Distribution of # of CFs by Utilization - Polypharmacy"),
        html.Hr(),
        dcc.Graph(figure=util_figs["Q78"]),
        dcc.Graph(figure=util_figs["Q85"]),
        dcc.Graph(figure=util_figs["Q91"]),
        dcc.Graph(figure=util_figs["Q93"]),
        dcc.Graph(figure=util_figs["Q96"]),
        dcc.Graph(figure=util_figs["Q103"]),
        html.Br(),
    ])