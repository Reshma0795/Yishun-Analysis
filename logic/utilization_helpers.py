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
    """
    Returns:
      counts_df: long-form counts
      fig: grouped bar chart (NOT stacked)
    """
    if cf_col not in df.columns or visits_bin_col not in df.columns:
        empty = pd.DataFrame(columns=[cf_col, "GP Visits Bin", "Count"])
        fig = px.bar(empty, x=cf_col, y="Count", title=f"{title} (No data)")
        return empty, fig

    tmp = df[[cf_col, visits_bin_col]].dropna().copy()
    if tmp.empty:
        empty = pd.DataFrame(columns=[cf_col, "GP Visits Bin", "Count"])
        fig = px.bar(empty, x=cf_col, y="Count", title=f"{title} (No data)")
        return empty, fig

    counts = (
        tmp.groupby([cf_col, visits_bin_col])
        .size()
        .reset_index(name="Count")
        .rename(columns={visits_bin_col: "GP Visits Bin"})
    )

    # enforce nice ordering
    if cf_order is not None:
        counts[cf_col] = pd.Categorical(counts[cf_col], categories=cf_order, ordered=True)

    counts["GP Visits Bin"] = pd.Categorical(
        counts["GP Visits Bin"], categories=list(bin_order), ordered=True
    )

    fig = px.bar(
        counts,
        x=cf_col,
        y="Count",
        color="GP Visits Bin",
        barmode="group",      # KEY: grouped bars, not stacked
        text="Count",
        title=title,
    )

    # styling to look less “traditional”
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(
        bargap=0.45,
        bargroupgap=0.18,
        title_x=0.02,
        legend_title_text="GP Visits",
        margin=dict(l=40, r=20, t=60, b=40),
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, zeroline=False)

    return counts, fig
