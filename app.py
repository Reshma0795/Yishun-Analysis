import dash
from dash import html, dcc
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc
import pandas as pd  # <-- needed to load your dataset

from logic.functional_assessment import add_FA_column, FA_layout
from logic.nursing_needs import add_nursing_column, Nursing_layout
from logic.rehab_needs import add_rehab_column, Rehab_layout
from logic.activation_own_care import add_activation_column, Activation_layout
from logic.disruptive_behavior import add_disruptive_column, Disruptive_layout
from logic.social_support import add_social_support_column, SocialSupport_layout
from logic.hospital_admissions import add_hospital_column, Hospital_layout
from logic.polypharmacy import add_polypharmacy_column, Polypharmacy_layout
from logic.global_impressions import GI_I_layout, GI_II_layout, GI_III_layout, GI_IV_layout, GI_V_layout
from logic.financial_challenges import add_financial_challenges_column, FinancialChallenges_layout
from logic.specialist_medical_service_needs import add_specialist_medical_service_needs_column, SpecialistMedicalServiceNeeds_layout
from logic.non_medical_resource_needs import add_non_medical_resource_needs_column, NonMedicalResourceNeeds_layout
from logic.value_count_page import ValueCounts_layout
from logic.gi_vs_cfs import layout as GI_vs_CFs_layout
from logic.organization_care import add_organization_of_care_column, OrganizationOfCare_layout
# ------------------------------------------------
# Load data ONCE (global)
# ------------------------------------------------
df = pd.read_excel("data/Yishun_Dataset.xlsx", sheet_name="Yishun_Dataset")
df = add_FA_column(df)  # this will add the Functional_Assessment column
df = add_nursing_column(df)
df = add_rehab_column(df)
df = add_activation_column(df)
df = add_disruptive_column(df)
df = add_social_support_column(df)
df = add_hospital_column(df)
df = add_polypharmacy_column(df)
df = add_financial_challenges_column(df)
df = add_specialist_medical_service_needs_column(df)
df = add_non_medical_resource_needs_column(df)
df = add_organization_of_care_column(df)
# ------------------------------------------------
# App setup
# ------------------------------------------------
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "Yishun Dashboard"

# ------------------------------------------------
# Styles
# ------------------------------------------------
SIDEBAR_STYLE = {
    "position": "fixed",
    "top": 0,
    "left": 0,
    "bottom": 0,
    "width": "260px",
    "padding": "20px 10px",
    "backgroundColor": "#261C5C",
    "color": "white",
    "overflowY": "auto",
}

CONTENT_STYLE = {
    "marginLeft": "270px",
    "marginRight": "20px",
    "padding": "20px 10px",
}

NAV_LINK_STYLE = {
    "fontSize": "14px",
    "padding": "8px 12px",
}

NAV_LINK_ACTIVE_STYLE = {
    "backgroundColor": "#483D99",
    "color": "white",
}

# ------------------------------------------------
# Sidebar Layout
# ------------------------------------------------
sidebar = html.Div(
    [
        html.H3("📊 DASHBOARD", className="mb-3", style={"fontWeight": "bold"}),
        html.Hr(style={"borderColor": "white"}),

        dbc.NavLink(
            "Overview",
            href="/healthcare-utilization-value-counts",
            id="link-hu-value-counts",
            style=NAV_LINK_STYLE,
            active="exact",
        ),
        html.Hr(style={"borderColor": "#645F9D"}),

        dbc.Nav(
            [
                # ---------- GLOBAL IMPRESSIONS ----------
                html.Div(
                    "GLOBAL IMPRESSIONS",
                    style={
                        "fontSize": "16px",
                        "fontWeight": "bold",
                        "marginTop": "10px",
                        "marginBottom": "4px",
                        "paddingLeft": "4px",
                    },
                ),

                dbc.NavLink(
                    "I – Healthy",
                    href="/gi-1-healthy",
                    id="link-gi-1",
                    style={**NAV_LINK_STYLE, "paddingLeft": "24px"},
                    active="exact",
                ),
                dbc.NavLink(
                    "II – Chronic, asymptomatic",
                    href="/gi-2-chronic-asymptomatic",
                    id="link-gi-2",
                    style={**NAV_LINK_STYLE, "paddingLeft": "24px"},
                    active="exact",
                ),
                dbc.NavLink(
                    "III – Chronic, stable symptomatic",
                    href="/gi-3-chronic-stable",
                    id="link-gi-3",
                    style={**NAV_LINK_STYLE, "paddingLeft": "24px"},
                    active="exact",
                ),
                dbc.NavLink(
                    "IV – Long course of decline",
                    href="/gi-4-long-decline",
                    id="link-gi-4",
                    style={**NAV_LINK_STYLE, "paddingLeft": "24px"},
                    active="exact",
                ),
                dbc.NavLink(
                    "V – Limited reserve & serious exacerbations",
                    href="/gi-5-limited-reserve",
                    id="link-gi-5",
                    style={**NAV_LINK_STYLE, "paddingLeft": "24px"},
                    active="exact",
                ),

                # ---------- COMPLICATING FACTORS ----------
                html.Div(
                    "COMPLICATING FACTORS",
                    style={
                        "fontSize": "16px",
                        "fontWeight": "bold",
                        "marginTop": "10px",
                        "marginBottom": "4px",
                        "paddingLeft": "4px",
                    },
                ),

                html.Hr(style={"borderColor": "#645F9D"}),

                dbc.NavLink(
                    "A. Functional Assessment",
                    href="/fa",
                    id="link-fa",
                    style=NAV_LINK_STYLE,
                    active="exact",
                ),
                html.Hr(style={"borderColor": "#645F9D"}),

                dbc.NavLink(
                    "B. Nursing type skilled task needs",
                    href="/nursing",
                    id="link-nursing",
                    style=NAV_LINK_STYLE,
                    active="exact",
                ),
                html.Hr(style={"borderColor": "#645F9D"}),

                dbc.NavLink(
                    "C. Rehabilitation type skilled task needs",
                    href="/rehab",
                    id="link-rehab",
                    style=NAV_LINK_STYLE,
                    active="exact",
                ),
                html.Hr(style={"borderColor": "#645F9D"}),

                dbc.NavLink(
                    "D. Organization of care",
                    href="/organization",
                    id="link-organization",
                    style=NAV_LINK_STYLE,
                    active="exact",
                ),
                html.Hr(style={"borderColor": "#645F9D"}),

                dbc.NavLink(
                    "E. Activation in own care",
                    href="/activation",
                    id="link-activation",
                    style=NAV_LINK_STYLE,
                    active="exact",
                ),
                html.Hr(style={"borderColor": "#645F9D"}),

                dbc.NavLink(
                    "F. Disruptive behavioural issues",
                    href="/disruptive",
                    id="link-disruptive",
                    style=NAV_LINK_STYLE,
                    active="exact",
                ),
                html.Hr(style={"borderColor": "#645F9D"}),

                dbc.NavLink(
                    "G. Social support in case of need",
                    href="/social-support",
                    id="link-social-support",
                    style=NAV_LINK_STYLE,
                    active="exact",
                ),
                html.Hr(style={"borderColor": "#645F9D"}),

                dbc.NavLink(
                    "H. Polypharmacy",
                    href="/polypharmacy",
                    id="link-polypharmacy",
                    style=NAV_LINK_STYLE,
                    active="exact",
                ),
                html.Hr(style={"borderColor": "#645F9D"}),

                dbc.NavLink(
                    "I. Hospital admissions (6 months)",
                    href="/hospital",
                    id="link-hospital",
                    style=NAV_LINK_STYLE,
                    active="exact",
                ),
                html.Hr(style={"borderColor": "#645F9D"}),

                dbc.NavLink(
                    "J. Financial challenges",
                    href="/financial",
                    id="link-financial",
                    style=NAV_LINK_STYLE,
                    active="exact",
                ),
                html.Hr(style={"borderColor": "#645F9D"}),

                dbc.NavLink(
                    "K. Specialist medical service needs",
                    href="/specialist",
                    id="link-specialist",
                    style=NAV_LINK_STYLE,
                    active="exact",
                ),
                html.Hr(style={"borderColor": "#645F9D"}),

                dbc.NavLink(
                    "L. Non-medical resource needs",
                    href="/non-medical",
                    id="link-non-medical",
                    style=NAV_LINK_STYLE,
                    active="exact",
                ),
                html.Hr(style={"borderColor": "#645F9D"}),

                # ✅ FIX: this link must be inside the children list
                dbc.NavLink(
                    "GI vs Complicating Factors",
                    href="/gi-vs-cfs",
                    id="link-gi-vs-cfs",
                    style=NAV_LINK_STYLE,
                    active="exact",
                ),
            ],
            vertical=True,
            pills=True,
        ),
    ],
    style=SIDEBAR_STYLE,
)

# ------------------------------------------------
# Placeholder content area
# ------------------------------------------------
content = html.Div(id="page-content", style=CONTENT_STYLE)

app.layout = html.Div([
    dcc.Location(id="url"),
    sidebar,
    content])
# ------------------------------------------------
# Page Routing Logic
# ------------------------------------------------
@app.callback(
    Output("page-content", "children"),
    Input("url", "pathname")
)
def render_page(pathname):

    if pathname == "/" or pathname is None:
        return html.Div([
            html.H2("Overview"),
            html.P("High-level summary of the Yishun dataset.")
        ])

    elif pathname == "/gi":
        return html.Div([
            html.H2("Global Impressions"),
            html.P("Insert GI charts/tables here.")
        ])
    elif pathname == "/fa": return FA_layout(df)
    elif pathname == "/nursing": return Nursing_layout(df)
    elif pathname == "/rehab": return Rehab_layout(df)
    elif pathname == "/organization": return OrganizationOfCare_layout(df)
    elif pathname == "/activation": return Activation_layout(df)
    elif pathname == "/disruptive": return Disruptive_layout(df)
    elif pathname == "/social-support": return SocialSupport_layout(df)
    elif pathname == "/polypharmacy": return Polypharmacy_layout(df)
    elif pathname == "/hospital": return Hospital_layout(df)
    elif pathname == "/financial": return FinancialChallenges_layout(df)
    elif pathname == "/specialist": return SpecialistMedicalServiceNeeds_layout(df)
    elif pathname == "/non-medical": return NonMedicalResourceNeeds_layout(df)
    elif pathname == "/gi-1-healthy": return GI_I_layout(df)
    elif pathname == "/gi-2-chronic-asymptomatic": return GI_II_layout(df)
    elif pathname == "/gi-3-chronic-stable": return GI_III_layout(df)
    elif pathname == "/gi-4-long-decline": return GI_IV_layout(df)
    elif pathname == "/gi-5-limited-reserve": return GI_V_layout(df)
    #elif pathname == "/gi-utilisation": return gi_utilisation.layout(df)
    elif pathname == "/healthcare-utilization-value-counts": return ValueCounts_layout(df)
    elif pathname == "/gi-vs-cfs": return GI_vs_CFs_layout(df)
    return html.Div([html.H2("404 – Page Not Found")])

# ------------------------------------------------
# Run App
# ------------------------------------------------
if __name__ == "__main__":
    app.run_server(debug=True)

