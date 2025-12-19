import pandas as pd
from dash import html, dcc, dash_table
import plotly.express as px
import dash_bootstrap_components as dbc

from logic.mapping_helpers import build_mapping_table
from logic.FA_helper import binary_question_group_table, response_summary_cards
from logic.demographics_helpers import add_age_bins, add_categorical_labels
from logic.cf_distribution_helpers import build_cf_value_column, cf_distribution_group_cf_on_y
from logic.utilization_helpers import build_gp_visits, add_visit_bins, gp_visits_by_cf_group
from logic.cf_matrix_tables import build_cf_matrix_row_pct_n_table
from logic.utilization import build_cf_x_utilization_binned_tables_per_question
from logic.question_texts import HEALTHCARE_UTILIZATION_QUESTIONS
from logic.ui_helpers import chart_card

# ------------------------------------------------------------
# 1. FUNCTION: Compute Functional Assessment Category
# ------------------------------------------------------------

Q155_cols = ["Q155_i", "Q155_ii", "Q155_iii", "Q155_iv", "Q155_v", "Q155_vi"]
Q167_cols = ["Q167_i", "Q167_ii", "Q167_iii", "Q167_iv", "Q167_v", "Q167_vi", "Q167_vii"]
Q155_labels = ["Bathing", "Dressing", "Transferring", "Using the toilet", "Continence", "Eating"]
Q167_labels = [
    "Handling personal finances",
    "Meal preparation",
    "Shopping",
    "Travelling",
    "Doing housework",
    "Using the telephone",
    "Taking Medications",
]
HC_UTIL_QUESTIONS = ["Q78", "Q85", "Q91", "Q93", "Q96", "Q103"]


def compute_FA_category(row):
    Q155 = row[Q155_cols].values
    Q167 = row[Q167_cols].values

    ADL_all_2 = all(x == 2 for x in Q155)      # No ADL deficit
    IADL_any_1 = any(x == 1 for x in Q167)     # At least one IADL deficit
    IADL_all_2 = all(x == 2 for x in Q167)     # No IADL deficit

    if ADL_all_2 and IADL_all_2:
        return 0
    elif ADL_all_2 and IADL_any_1:
        return 1
    elif IADL_any_1:
        return 2
    return None


# ------------------------------------------------------------
# 2. FUNCTION: Add the FA column to dataframe
# ------------------------------------------------------------
def add_FA_column(df):
    df["Functional_Assessment"] = df.apply(compute_FA_category, axis=1)
    return df


# ------------------------------------------------------------
# 3. Legend helper
# ------------------------------------------------------------

FA_LEGEND_LABELS = {
    "0": "0: No deficit",
    "1": "1: Any IADL deficit only, no ADL deficit",
    "2": "2: Any ADL deficit",
    "0.0": "0: No deficit",
    "1.0": "1: Any IADL deficit only, no ADL deficit",
    "2.0": "2: Any ADL deficit",
}


def rename_fa_legend(fig):
    fig.for_each_trace(lambda t: t.update(name=FA_LEGEND_LABELS.get(str(t.name), t.name)))
    return fig


# ------------------------------------------------------------
# 4. PAGE LAYOUT
# ------------------------------------------------------------
def FA_layout(df):
    # Make sure FA is available
    if "Functional_Assessment" not in df.columns:
        df = add_FA_column(df)

    # -----------------------
    # Q155 / Q167 tables & cards
    # -----------------------
    q155_cards = response_summary_cards(
        df,
        cols=Q155_cols,
        title="Q155 – ADL responses",
    )

    q167_cards = response_summary_cards(
        df,
        cols=Q167_cols,
        title="Q167 – IADL responses",
    )

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

    # -----------------------
    # Category counts
    # -----------------------
    count_table = pd.DataFrame(
        {
            "Category": [0, 1, 2],
            "Meaning": [
                "0: No deficit",
                "1: Any IADL deficit only, no ADL deficit",
                "2: Any ADL deficit",
            ],
            "Count": [
                int(df["Functional_Assessment"].eq(0).sum()),
                int(df["Functional_Assessment"].eq(1).sum()),
                int(df["Functional_Assessment"].eq(2).sum()),
            ],
        }
    )

    # (Optional) simple distribution chart – kept here but not displayed (same pattern as Nursing)
    fig = px.bar(
        count_table,
        x="Meaning",
        y="Count",
        title="Functional Assessment Distribution",
        text="Count",
        color="Category",
    )

    # -----------------------
    # Mapping table
    # -----------------------
    mapping_rows = [
        {
            "Complicating Factor": "A. Functional Assessment",
            "Mapped Question No from Survey": "Q155 & Q167",
            "Question Description": (
                "Q155 – ADL –\n"
                "Do you have any problem with any of the following:\n"
                "(i) Bathing\n"
                "(ii) Dressing\n"
                "(iii) Transferring\n"
                "(iv) Using the toilet\n"
                "(v) Continence\n"
                "(vi) Eating\n\n"
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
            "Levels": (
                "0: No deficit\n\n"
                "1: Any IADL deficit only, no ADL deficit\n\n"
                "2: Any ADL deficit"
            ),
            "Data Mapping": (
                "Q155 –\n 1) Yes\n 2) No\n 777) X (Refused)\n\n"
                "Q167 –\n 1) Yes\n 2) No\n 777) X (Refused)\n 999) Not applicable"
            ),
            "Coding": (
                "If Q155_i to Q155_vi == 2 AND\n"
                "   Q167_i to Q167_vii == 2 then\n"
                "   0: No deficit\n\n"
                "If any Q167_i to Q167_vii == 1 AND\n"
                "   Q155_i to Q155_vi == 2 then\n"
                "   1: Any IADL deficit only, no ADL deficit\n\n"
                "If any Q155_i to Q155_vi == 1 then\n"
                "   2: Any ADL deficit"
            ),
        }
    ]
    mapping_table = build_mapping_table(mapping_rows, title="CF A - Functional Assessment Mapping")

    # -----------------------
    # Demographics + CF prep
    # -----------------------
    df_demo = add_age_bins(df, age_col="Q2", out_col="Age_Bin")
    df_demo = add_categorical_labels(
        df_demo,
        mappings={
            "Gender_Label": {"source": "Q4", "map": {1: "Male", 2: "Female"}},
            "Ethnicity_Label": {
                "source": "Q3",
                "map": {1: "Chinese", 2: "Malay", 3: "Indian", 4: "Others"},
            },
        },
    )

    df_demo = build_cf_value_column(
        df_demo,
        source_col="Functional_Assessment",
        out_col="FA_CF_Value",
        allowed_values={0, 1, 2},
    )

    age_order = ["<40", "40–65", "65–85", ">=85"]
    gender_order = ["Male", "Female"]
    eth_order = ["Chinese", "Malay", "Indian", "Others"]

    # -----------------------
    # CF matrix (column-wise % within each subgroup)
    # -----------------------
    fa_matrix = build_cf_matrix_row_pct_n_table(
        df_demo=df_demo,
        cf_col="Functional_Assessment",
        category_order=[0, 1, 2],
        category_labels={
            0: "0: No deficit",
            1: "1: Any IADL deficit only, no ADL deficit",
            2: "2: Any ADL deficit",
        },
        title="Complicating Factor: Functional Assessment (%, n)",
        total_denominator=2499,  # adjust if your overall N changes
    )

    # -----------------------
    # Utilisation tables (per-question, like Nursing)
    # -----------------------
    util_tables = build_cf_x_utilization_binned_tables_per_question(
        df_demo=df_demo,
        cf_col="Functional_Assessment",
        category_order=[0, 1, 2],
        category_labels={
            0: "0: No deficit",
            1: "1: Any IADL deficit only, no ADL deficit",
            2: "2: Any ADL deficit",
        },
        util_qcodes=HC_UTIL_QUESTIONS,
        util_question_meta=HEALTHCARE_UTILIZATION_QUESTIONS,
        title_prefix="CF A (Functional Assessment) × Healthcare Utilization (0 / 1–2 / 3–5 / 6+)",
        show_pct=True,
    )

    # -----------------------
    # CF distribution by demographics (column-wise % within each group)
    # -----------------------
    age_counts, age_fig = cf_distribution_group_cf_on_y(
        df_demo=df_demo,
        cf_col="Functional_Assessment",
        group_col="Age_Bin",
        cf_order=[0, 1, 2],
        group_order=age_order,
        title="Functional Assessment: CF distribution within each Age Bin",
        legend_title="CF Category",
    )

    gender_counts, gender_fig = cf_distribution_group_cf_on_y(
        df_demo=df_demo,
        cf_col="Functional_Assessment",
        group_col="Gender_Label",
        cf_order=[0, 1, 2],
        group_order=gender_order,
        title="Functional Assessment: CF distribution within each Gender group",
        legend_title="CF Category",
    )

    eth_counts, eth_fig = cf_distribution_group_cf_on_y(
        df_demo=df_demo,
        cf_col="Functional_Assessment",
        group_col="Ethnicity_Label",
        cf_order=[0, 1, 2],
        group_order=eth_order,
        title="Functional Assessment: CF distribution within each Ethnicity group",
        legend_title="CF Category",
    )

    age_fig = rename_fa_legend(age_fig)
    gender_fig = rename_fa_legend(gender_fig)
    eth_fig = rename_fa_legend(eth_fig)

    # -----------------------
    # Utilisation charts (same pattern as Nursing)
    # -----------------------
    fa_order = [0, 1, 2]
    util_figs = {}

    for qcode in HC_UTIL_QUESTIONS:
        df_demo = build_gp_visits(df_demo, source_col=qcode, out_col="GP_Visits")
        df_demo = add_visit_bins(df_demo, visits_col="GP_Visits", out_col="GP_Visits_Bin")

        meta = HEALTHCARE_UTILIZATION_QUESTIONS.get(qcode, {})
        util_title = meta.get("title", qcode)

        _, fig_util = gp_visits_by_cf_group(
            df_demo,
            cf_col="Functional_Assessment",
            cf_order=fa_order,
            title=f"{qcode}: {util_title} - Cross with Functional Assessment",
        )

        fig_util.update_layout(legend_title_text=util_title)
        util_figs[qcode] = fig_util

    # -----------------------
    # Layout (mirroring Nursing page)
    # -----------------------
    return html.Div(
        [
            mapping_table,
            html.Br(),
            dbc.Row(
                [
                    dbc.Col(q155_table, width=6),
                    dbc.Col(q167_table, width=6),
                ],
                className="mb-4",
            ),
            # If you want the cards, uncomment these:
            # q155_cards,
            # q167_cards,
            html.Hr(),
            html.H4("Distribution of # of Categories – Functional Assessment"),
            dash_table.DataTable(
                data=count_table.to_dict("records"),
                columns=[{"name": i, "id": i} for i in count_table.columns],
                style_cell={"textAlign": "center"},
                style_header={"fontWeight": "bold"},
            ),
            html.Br(),
            # Optional: show bar chart
            # dcc.Graph(figure=fig),
            html.Hr(),
            fa_matrix,
            html.Br(),
            html.Hr(),
            util_tables,
            html.Br(),
            html.Hr(),
            html.H3("Distribution of # of CFs by Demographics (Functional Assessment)"),
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
            html.H3("Distribution of # of CFs by Utilization (Functional Assessment)"),
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
