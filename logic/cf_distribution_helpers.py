import pandas as pd
import plotly.express as px


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


def cf_distribution_by_group(
    df: pd.DataFrame,
    cf_count_col: str,
    group_col: str,
    group_order=None,
    title: str = "",
    cf_label: str = "CF Count",
):
    """
    Returns:
      counts_df: group_col x CF_count (0/1/2/...) counts in long form
      fig: stacked bar chart
    """
    if group_col not in df.columns or cf_count_col not in df.columns:
        empty = pd.DataFrame(columns=[group_col, cf_label, "Count"])
        fig = px.bar(empty, x=group_col, y="Count", title=f"{title} (No data)")
        return empty, fig

    tmp = df[[group_col, cf_count_col]].dropna().copy()
    if tmp.empty:
        empty = pd.DataFrame(columns=[group_col, cf_label, "Count"])
        fig = px.bar(empty, x=group_col, y="Count", title=f"{title} (No data)")
        return empty, fig

    counts = (
        tmp.groupby([group_col, cf_count_col])
        .size()
        .reset_index(name="Count")
        .rename(columns={cf_count_col: cf_label})
    )

    # readable labels for 0/1 binary case
    if set(counts[cf_label].unique()).issubset({0, 1}):
        counts[cf_label] = counts[cf_label].map({0: "0 CFs", 1: "1 CF"})

    if group_order:
        counts[group_col] = pd.Categorical(counts[group_col], categories=group_order, ordered=True)

    # Make CF values categorical so Plotly treats them as discrete bars (0/1/2)
    counts[cf_label] = counts[cf_label].astype(str)

    fig = px.bar(
        counts,
        x=group_col,          # Gender / Age_Bin / Ethnicity on X
        y="Count",
        color=cf_label,       # CF 0/1/2 become the 3 bars
        barmode="group",      # <-- KEY: grouped (side-by-side), not stacked
        text="Count",
        title=title,
    )

    fig.update_traces(textposition="outside", cliponaxis=False)

    # optional spacing tweaks so bars don’t look cramped
    fig.update_layout(
        bargap=0.35,          # space between Male vs Female groups
        bargroupgap=0.10,     # space between CF bars inside a group
        legend_title_text=cf_label,
    )


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
# ------------------------------------------------------------