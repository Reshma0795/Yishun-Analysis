import pandas as pd
import plotly.express as px

# -------------------------------
# Q78 cleaner (single-column)
# -------------------------------
def build_gp_visits(
    df: pd.DataFrame,
    source_col: str = "Q78",
    out_col: str = "GP_Visits",
    missing_codes={666, 777},  # 666 Unable to recall, 777 Refused
):
    """
    Converts single-column Q78 into a clean numeric visit count:
      - 0 stays 0
      - 1..n stays numeric
      - 666/777/NaN -> None
    """
    df = df.copy()

    if source_col not in df.columns:
        df[out_col] = None
        return df

    def to_num(v):
        if pd.isna(v):
            return None
        try:
            v = int(v)
        except (TypeError, ValueError):
            return None

        if v in missing_codes:
            return None
        if v < 0:
            return None
        return v

    df[out_col] = df[source_col].apply(to_num)
    return df


def add_visit_bins(
    df: pd.DataFrame,
    visits_col: str = "GP_Visits",
    out_col: str = "GP_Visits_Bin",
):
    """
    Bins GP visits for readable plots:
      0, 1–2, 3–5, 6+
    """
    df = df.copy()

    if visits_col not in df.columns:
        df[out_col] = None
        return df

    def bin_it(v):
        if pd.isna(v):
            return None
        v = int(v)
        if v == 0:
            return "0"
        if 1 <= v <= 2:
            return "1–2"
        if 3 <= v <= 5:
            return "3–5"
        return "6+"

    df[out_col] = df[visits_col].apply(bin_it)
    return df


def gp_visits_by_cf_group(
    df: pd.DataFrame,
    cf_col: str,
    visits_bin_col: str = "GP_Visits_Bin",
    cf_order=None,
    bin_order=("0", "1–2", "3–5", "6+"),
    title="Q78 (Private GP visits) by CF",
):
    if cf_col not in df.columns or visits_bin_col not in df.columns:
        empty = pd.DataFrame(columns=[cf_col, "GP Visits Bin", "Count"])
        fig = px.bar(empty, x=cf_col, y="Count", title=f"{title} (No data)")
        return empty, fig

    tmp = df[[cf_col, visits_bin_col]].dropna().copy()
    if tmp.empty:
        empty = pd.DataFrame(columns=[cf_col, "GP Visits Bin", "Count"])
        fig = px.bar(empty, x=cf_col, y="Count", title=f"{title} (No data)")
        return empty, fig

    # -----------------------------
    # 1️⃣ COUNT DATA
    # -----------------------------
    counts = (
        tmp.groupby([cf_col, visits_bin_col])
        .size()
        .reset_index(name="Count")
        .rename(columns={visits_bin_col: "GP Visits Bin"})
    )

    # Ordering
    if cf_order is not None:
        counts[cf_col] = pd.Categorical(
            counts[cf_col], categories=cf_order, ordered=True
        )

    counts["GP Visits Bin"] = pd.Categorical(
        counts["GP Visits Bin"], categories=list(bin_order), ordered=True
    )

    # -----------------------------
    # 2️⃣ PERCENT CALCULATION  ✅ THIS IS WHERE IT GOES
    # -----------------------------
    counts["Total_CF"] = counts.groupby(cf_col)["Count"].transform("sum")
    counts["Percent"] = (counts["Count"] / counts["Total_CF"]) * 100

    # -----------------------------
    # 3️⃣ PLOT
    # -----------------------------
    fig = px.bar(
        counts,
        x=cf_col,
        y="Percent",
        color="GP Visits Bin",
        barmode="group",
        text=counts.apply(
            lambda r: f"{r['Percent']:.1f}%\n(n={r['Count']})",
            axis=1,
        ),
    )
    fig.update_traces(
    textfont=dict(
        size=13,          # 🔼 increase text size
        color="white",    # good contrast
        family="Inter, Arial"
    ),
    insidetextanchor="middle",
)

    # -----------------------------
    # 4️⃣ STYLING  ✅ THIS IS WHERE IT GOES
    # -----------------------------
    fig.update_traces(
        textposition="inside",
        textfont=dict(size=11, color="white"),
        insidetextanchor="middle",
        cliponaxis=False,
    )

    fig.update_layout(
        plot_bgcolor="white",
        paper_bgcolor="white",

        legend=dict(
            title_text="Visits",
            font=dict(size=11),
            yanchor="top",
            y=0.98,
            xanchor="right",
            x=0.98,
            bgcolor="rgba(255,255,255,0.85)",
            bordercolor="rgba(0,0,0,0.1)",
            borderwidth=1,
        ),

        yaxis=dict(
            title="Percent (%)",
            ticksuffix="%",
            showgrid=True,
            gridcolor="rgba(0,0,0,0.08)",
            zeroline=False,
        ),
        xaxis=dict(
            title=cf_col,
            showgrid=False,
        ),

        bargap=0.15,
        bargroupgap=0.05,
        margin=dict(l=50, r=30, t=70, b=50),

        title=dict(
            x=0.02,
            font=dict(size=15, weight=600),
        ),
    )

    fig.update_layout(
    legend=dict(
        orientation="h",
        yanchor="top",
        y=-0.25,          # ⬇ move below plot
        xanchor="center",
        x=0.5,
        font=dict(size=11),
        title=None,
    ),
    margin=dict(b=90),   # give space for legend
)

    return counts, fig

