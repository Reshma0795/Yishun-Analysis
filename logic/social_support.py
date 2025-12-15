import pandas as pd
from dash import html, dcc, dash_table
import plotly.express as px
import dash_bootstrap_components as dbc

from logic.mapping_helpers import build_mapping_table
from logic.social_support_helper import binary_question_group_table

from logic.demographics_helpers import add_age_bins, add_categorical_labels
from logic.cf_distribution_helpers import build_cf_value_column, cf_distribution_by_group
from logic.utilization_helpers import build_gp_visits, add_visit_bins, gp_visits_by_cf_group
from logic.question_texts import HEALTHCARE_UTILIZATION_QUESTIONS

# --------------------------------------------
# Columns for Lubben social network items
# --------------------------------------------
HC_UTIL_QUESTIONS = ["Q78", "Q85", "Q91", "Q93", "Q96", "Q103"]
FAMILY_COLS = ["Q193", "Q194", "Q195"]
FRIEND_COLS = ["Q196", "Q197", "Q198"]
ALL_LUBBEN_COLS = FAMILY_COLS + FRIEND_COLS

# Map raw codes to approximate counts (only 0 vs >0 matters)
LUBBEN_MAP = {
    1: 0,   # 0 people
    2: 1,   # 1 person
    3: 2,   # 2 people
    4: 3,   # 3-4  (we use 3 as a representative)
    5: 5,   # 5-8  (we use 5 as a representative)
    6: 9,   # >=9
    # 777 / 999 will be treated as missing/ignored
}

# --------------------------------------------
# Compute Social Support Category
# --------------------------------------------
def compute_social_support_category(row):
    # Map Lubben responses (only accept codes 1..6; 777/999/NaN become None)
    def _val(col):
        v = row.get(col)
        return LUBBEN_MAP.get(v, None)

    q193 = _val("Q193")
    q194 = _val("Q194")
    q195 = _val("Q195")
    q196 = _val("Q196")
    q197 = _val("Q197")
    q198 = _val("Q198")

    # STRICT: if any is missing/invalid -> not scored
    if any(v is None for v in [q193, q194, q195, q196, q197, q198]):
        return None

    # Your exact logic:
    # if [sum Q193 - Q194 >0 and Q195 >0] OR [sum Q196 - Q197 >0 AND Q198 >0] then 0
    if ((q193 + q194) > 0 and q195 > 0) or ((q196 + q197) > 0 and q198 > 0):
        return 0  # has support

    # else if [sum Q193 - Q198] = 0 then 2
    if (q193 + q194 + q195 + q196 + q197 + q198) == 0:
        return 2  # has no support

    # else 1
    return 1  # no support for basic healthcare but companionship

# --------------------------------------------
# Add Column to DataFrame
# --------------------------------------------
def add_social_support_column(df):
    df["Social_Support_CF"] = df.apply(compute_social_support_category, axis=1)
    return df

# --------------------------------------------
# Layout for Dash Page
# --------------------------------------------
def SocialSupport_layout(df):

    # Ensure CF column exists
    if "Social_Support_CF" not in df.columns:
        df = add_social_support_column(df)

    # -----------------------
    # Category counts (0/1/2)
    # -----------------------
    count_table = pd.DataFrame({
        "Category": [0, 1, 2],
        "Meaning": [
            "0 = has support for both basic healthcare services and companionship",
            "1 = no support for either basic healthcare services or companionship",
            "2 = dysfunctional social circumstance"
        ],
        "Count": [
            df["Social_Support_CF"].eq(0).sum(),
            df["Social_Support_CF"].eq(1).sum(),
            df["Social_Support_CF"].eq(2).sum(),
        ]
    })

    # (Optional chart – you already had it)
    fig = px.bar(
        count_table,
        x="Meaning",
        y="Count",
        title="G. Social Support in Case of Need – Distribution",
        text="Count",
        color="Category"
    )

    # -----------------------
    # Mapping table
    # -----------------------
    mapping_rows = [
        {
            "Complicating Factor": "G. Social support in case of need",
            "Mapped Question No from Survey": "Q193–Q198",
            "Question Description": (
                "Q193. How many relatives do you see or hear from at least once a month?\n\n"
                "Q194. How many relatives do you feel at ease with whom you can talk about private matters?\n\n"
                "Q195. How many relatives do you feel close to such that you could call on them for help?\n\n"
                "Q196. How many of your friends do you see or hear from at least once a month?\n\n"
                "Q197. How many friends do you feel at ease with whom you can talk about private matters?\n\n"
                "Q198. How many friends do you feel close to such that you could call on them for help?"
            ),
            "Levels": (
                "0 = has support for both basic healthcare services and companionship\n\n"
                "1 = no support for basic healthcare services but companionship\n\n"
                "2 = has no support"
            ),
            "Data Mapping": (
                "Q193–Q198 –\n"
                " 1) 0\n"
                " 2) 1\n"
                " 3) 2\n"
                " 4) 3–4\n"
                " 5) 5–8\n"
                " 6) ≥9\n"
                " 777) X (Refused)\n"
                " 999) Not Applicable"
            ),
            "Coding": (
                "If [sum(Q193–Q194) > 0 AND Q195 > 0]\n"
                "OR [sum(Q196–Q197) > 0 AND Q198 > 0]\n"
                "Then: 0 (has support)\n\n"
                "Else if [sum(Q193–Q198) = 0]\n"
                "Then: 2 (has no support)\n\n"
                "Else: 1 (no support for basic healthcare but companionship)"
            ),
        }
    ]

    mapping_table = build_mapping_table(mapping_rows, title="CF G - Social support in case of need")

    # -----------------------
    # Value-counts table block (Q193–Q198)
    # -----------------------
    lubben_value_counts_table = binary_question_group_table(
        df,
        cols=ALL_LUBBEN_COLS,
        row_labels=[
            "Q193 – Relatives seen/heard from monthly",
            "Q194 – Relatives to talk private matters",
            "Q195 – Relatives you can call for help",
            "Q196 – Friends seen/heard from monthly",
            "Q197 – Friends to talk private matters",
            "Q198 – Friends you can call for help",
        ],
        # IMPORTANT: dataset codes are 1..6 (where 1 means “0”, 2 means “1”, etc.)
        code_0=1,
        code_1=2,
        code_2=3,
        code_3_4=4,
        code_5_8=5,
        code_9_plus=6,
        code_refused=777,
        code_not_applicable=999,
        title_text="Value Counts for Q193–Q198 (dataset code: 1→0, 2→1, 3→2, 4→3–4, 5→5–8, 6→≥9)",
    )

    # -----------------------
    # Demographics distribution (0/1/2)
    # -----------------------
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
        source_col="Social_Support_CF",
        out_col="SocialSupport_CF_Value",
        allowed_values={0, 1, 2},
    )

    age_order = ["<40", "40–65", "65–85", ">=85"]
    gender_order = ["Male", "Female"]
    eth_order = ["Chinese", "Malay", "Indian", "Others"]

    age_counts, age_fig = cf_distribution_by_group(
        df_demo,
        cf_count_col="SocialSupport_CF_Value",
        group_col="Age_Bin",
        group_order=age_order,
        title="Social Support: Distribution by Age Bin (0/1/2)",
        cf_label="Social Support CF Level",
    )

    gender_counts, gender_fig = cf_distribution_by_group(
        df_demo,
        cf_count_col="SocialSupport_CF_Value",
        group_col="Gender_Label",
        group_order=gender_order,
        title="Social Support: Distribution by Gender (0/1/2)",
        cf_label="Social Support CF Level",
    )

    eth_counts, eth_fig = cf_distribution_by_group(
        df_demo,
        cf_count_col="SocialSupport_CF_Value",
        group_col="Ethnicity_Label",
        group_order=eth_order,
        title="Social Support: Distribution by Ethnicity (0/1/2)",
        cf_label="Social Support CF Level",
    )

    # -----------------------
    # Healthcare utilization cross (Q78..Q103) vs Social_Support_CF (0/1/2)
    # -----------------------
    social_order = [0, 1, 2]
    util_figs = {}

    for qcode in HC_UTIL_QUESTIONS:
        df_demo = build_gp_visits(df_demo, source_col=qcode, out_col="GP_Visits")
        df_demo = add_visit_bins(df_demo, visits_col="GP_Visits", out_col="GP_Visits_Bin")
        meta = HEALTHCARE_UTILIZATION_QUESTIONS.get(qcode, {})
        util_title = meta.get("title", qcode)
        _, fig_util = gp_visits_by_cf_group(
            df_demo,
            cf_col="Social_Support_CF",
            cf_order=social_order,
            title=f"{qcode}: {util_title} - Cross with Social Support in Case of Need",
        )
        util_figs[qcode] = fig_util

    # -----------------------
    # Return layout
    # -----------------------
    return html.Div([
        mapping_table,
        html.Br(),
        lubben_value_counts_table,
        html.Hr(),
        html.H4("Distribution of # of Categories - Social Support in Case of Need"),
        html.Hr(),
        dash_table.DataTable(
            data=count_table.to_dict("records"),
            columns=[{"name": c, "id": c} for c in count_table.columns],
            style_cell={"textAlign": "center"},
            style_header={"fontWeight": "bold"},
        ),
        html.Br(),
        # (optional)
        # dcc.Graph(figure=fig),
        html.Hr(),
        html.H3("Distribution of # of CFs by Demographics - Social Support in Case of Need"),
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
        html.H3("Distribution of # of CFs by Utilization - Social Support in Case of Need"),
        html.Hr(),
        dcc.Graph(figure=util_figs["Q78"]),
        dcc.Graph(figure=util_figs["Q85"]),
        dcc.Graph(figure=util_figs["Q91"]),
        dcc.Graph(figure=util_figs["Q93"]),
        dcc.Graph(figure=util_figs["Q96"]),
        dcc.Graph(figure=util_figs["Q103"]),
        html.Br(),
    ])
