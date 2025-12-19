import pandas as pd
import plotly.express as px
from logic.plot_style import apply_modern_bar_style

def build_binary_cf_count(
    df: pd.DataFrame,
    source_col: str,
    out_col: str,
    present_values,
    absent_values=None,
):
    """
    Creates a 0/1 CF-count column for any CF column.

      - 1 if df[source_col] in present_values
      - 0 if df[source_col] in absent_values (optional)
      - None otherwise (missing/unscored/unusable)

    present_values: set/list/tuple
    absent_values: set/list/tuple or None
    """
    present_values = set(present_values)
    absent_values = set(absent_values) if absent_values is not None else None

    def mapper(v):
        if pd.isna(v):
            return None
        try:
            v2 = int(v)
        except (TypeError, ValueError):
            return None

        if v2 in present_values:
            return 1
        if absent_values is not None and v2 in absent_values:
            return 0
        return None

    df = df.copy()
    if source_col not in df.columns:
        df[out_col] = None
        return df

    df[out_col] = df[source_col].apply(mapper)
    return df


def cf_distribution_rowwise_by_group(
    df_demo: pd.DataFrame,
    *,
    cf_col: str,              # e.g. "Nursing_Needs_Imputed"
    group_col: str,           # e.g. "Age_Bin" / "Gender_Label" / "Ethnicity_Label"
    cf_order,
    group_order,
    title: str,
    legend_title: str,
    pct_decimals: int = 1,
):
    """
    ROW-WISE % by CF category (matches your matrix subgroup cells):
      pct = n(group within CF cat) / n(CF cat) * 100

    Chart style matches utilization:
      x = CF category
      color = group
      barmode = group (side-by-side)
      y = Percent
      text = "% (n=)"
    """
    tmp = df_demo[[cf_col, group_col]].dropna().copy()
    tmp = tmp[tmp[cf_col].isin(cf_order)]
    tmp = tmp[tmp[group_col].isin(group_order)]
    if tmp.empty:
        empty = pd.DataFrame(columns=["CF", "Group", "n", "Percent", "Label"])
        fig = px.bar(empty, x="CF", y="Percent", color="Group", barmode="group", title=title)
        fig.update_layout(template="plotly_white")
        return empty, fig
    tmp["CF"] = pd.Categorical(tmp[cf_col], categories=list(cf_order), ordered=True)
    tmp["Group"] = pd.Categorical(tmp[group_col], categories=list(group_order), ordered=True)
    counts = (
        tmp.groupby(["CF", "Group"])
        .size()
        .reset_index(name="n"))
    cf_totals = counts.groupby("CF")["n"].sum().reset_index(name="cf_total")
    counts = counts.merge(cf_totals, on="CF", how="left")
    counts["Percent"] = (counts["n"] / counts["cf_total"]) * 100.0
    counts["Label"] = counts.apply(
        lambda r: f"{r['Percent']:.{pct_decimals}f}%\n(n={int(r['n'])})" if r["n"] > 0 else "",
        axis=1,
    )
    fig = px.bar(
        counts,
        x="CF",
        y="Percent",
        color="Group",
        barmode="group",    
        text="Label",
        title=title,
        labels={"CF": "", "Percent": "Percent (%)", "Group": legend_title},
    )
    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="white",
        plot_bgcolor="white",
        title_x=0.02,
        margin=dict(l=40, r=20, t=60, b=70),
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.22,
            xanchor="left",
            x=0.0,
            font=dict(size=11),
            title_text=legend_title,
        ),
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, zeroline=False, ticksuffix="%")
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(uniformtext_minsize=10, uniformtext_mode="hide")
    return counts, fig

def build_cf_value_column(
    df: pd.DataFrame,
    source_col: str,
    out_col: str,
    allowed_values=None,
):
    """
    Copies a CF column as-is (e.g. 0/1/2) into a new column,
    optionally filtering to allowed values.

    - Keeps original CF levels
    - Does NOT binarise
    """

    df = df.copy()

    if source_col not in df.columns:
        df[out_col] = None
        return df

    def mapper(v):
        if pd.isna(v):
            return None
        try:
            v = int(v)
        except (TypeError, ValueError):
            return None

        if allowed_values is not None and v not in allowed_values:
            return None
        return v

    df[out_col] = df[source_col].apply(mapper)
    return df

def style_plotly_card(fig, title=None):
    """Make Plotly charts look like modern dashboard cards."""
    fig.update_layout(
        title={"text": title or fig.layout.title.text, "x": 0.02, "xanchor": "left"},
        font={"family": "Inter, Segoe UI, Arial", "size": 13},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin={"l": 30, "r": 20, "t": 55, "b": 35},
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            title=None,
        ),
        xaxis=dict(
            showgrid=True,
            gridcolor="rgba(0,0,0,0.06)",
            zeroline=False,
            linecolor="rgba(0,0,0,0.10)",
            tickfont={"size": 12},
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="rgba(0,0,0,0.06)",
            zeroline=False,
            linecolor="rgba(0,0,0,0.10)",
            tickfont={"size": 12},
        ),
    )

    # cleaner hover
    fig.update_traces(
        hovertemplate="<b>%{x}</b><br>%{legendgroup}: %{y}<extra></extra>",
    )
    return fig


def cf_distribution_group_cf_on_y(
    df_demo: pd.DataFrame,
    *,
    cf_col: str,              # e.g. "Nursing_Needs_Imputed"
    group_col: str,           # e.g. "Age_Bin" / "Gender_Label" / "Ethnicity_Label"
    cf_order,
    group_order,
    title: str,
    legend_title: str,
    pct_decimals: int = 1,
):
    """
    Column-wise (group-wise) % calculation:

        For each group G (e.g. age bin <40):

            Percent(CF=k | G) =
                (# respondents in group G with CF = k) /
                (total # respondents in group G) * 100

        - x-axis:   group (Age/Gender/Ethnicity)
        - bars:     CF = 0,1,2 side-by-side under each group
        - y-axis:   Percent of that group
        - text:     "<pct>% (n=...)"
    """

    # 1) Total people in each group (denominator) – only require group to be present
    grp_only = df_demo[[group_col]].dropna().copy()
    grp_only = grp_only[grp_only[group_col].isin(group_order)]
    group_totals = (
        grp_only.groupby(group_col)
        .size()
        .reset_index(name="group_total")
        .rename(columns={group_col: "Group"})
    )

    # 2) Counts of each CF within each group (numerator)
    tmp = df_demo[[cf_col, group_col]].dropna().copy()
    tmp = tmp[tmp[group_col].isin(group_order)]
    tmp = tmp[tmp[cf_col].isin(cf_order)]

    tmp["Group"] = tmp[group_col]
    tmp["CF"] = tmp[cf_col]

    raw_counts = (
        tmp.groupby(["Group", "CF"])
        .size()
        .reset_index(name="n")
    )

    # 3) Ensure every (Group, CF) combo exists, even if n = 0
    all_combos = pd.DataFrame(
        [(g, c) for g in group_order for c in cf_order],
        columns=["Group", "CF"],
    )
    counts = all_combos.merge(raw_counts, on=["Group", "CF"], how="left")
    counts["n"] = counts["n"].fillna(0).astype(int)

    # 4) Attach total # people in each group (denominator)
    counts = counts.merge(group_totals, on="Group", how="left")

    # 5) Column-wise percent: n(CF=k & group G) / total(group G)
    counts["Percent"] = counts.apply(
        lambda r: (r["n"] / r["group_total"] * 100.0)
        if (pd.notna(r["group_total"]) and r["group_total"] > 0)
        else 0.0,
        axis=1,
    )

    # 6) Nice label text
    counts["Label"] = counts.apply(
        lambda r: f"{r['Percent']:.{pct_decimals}f}% (n={int(r['n'])})"
        if r["n"] > 0
        else "",
        axis=1,
    )

    # Keep order stable
    counts["Group"] = pd.Categorical(counts["Group"], categories=list(group_order), ordered=True)
    counts["CF"] = pd.Categorical(counts["CF"], categories=list(cf_order), ordered=True)

    fig = px.bar(
        counts,
        x="Group",
        y="Percent",
        color="CF",
        barmode="group",  # CF 0/1/2 together under each bin
        text="Label",
        title=title,
        labels={
            "Group": "",
            "Percent": "Percent (%)",
            "CF": legend_title,
        },
    )

    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="white",
        plot_bgcolor="white",
        title_x=0.02,
        margin=dict(l=40, r=20, t=60, b=70),
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.22,
            xanchor="left",
            x=0.0,
            font=dict(size=11),
            title_text=legend_title,
        ),
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, zeroline=False, ticksuffix="%")
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(uniformtext_minsize=10, uniformtext_mode="hide")

    return counts, fig


