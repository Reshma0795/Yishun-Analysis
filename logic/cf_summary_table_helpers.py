# logic/cf_summary_table_helpers.py
import pandas as pd

def build_cf_demographics_summary_table(
    df: pd.DataFrame,
    cf_col: str,
    category_order,
    category_labels: dict,
    age_col: str = "Age_Bin",
    gender_col: str = "Gender_Label",
    eth_col: str = "Ethnicity_Label",
    age_order=None,
    gender_order=None,
    eth_order=None,
    pct_decimals: int = 1,
):
    """
    Builds the "wide" summary table like your screenshot:

    Rows: CF categories
    Cols: Total, Age bins, Gender, Ethnicity
    Values: column-wise % (each column sums ~100% across categories)

    Notes:
    - Excludes missing CF (NaN/None) from denominators.
    - "Total" is across ALL valid CF rows.
    """

    if age_order is None:
        age_order = ["<40", "40–65", "65–85", ">=85"]
    if gender_order is None:
        gender_order = ["Male", "Female"]
    if eth_order is None:
        eth_order = ["Chinese", "Malay", "Indian", "Others"]

    # Keep only rows where CF is valid (0/1/2)
    dfv = df[df[cf_col].isin(category_order)].copy()

    def pct_series(counts: pd.Series) -> pd.Series:
        total = counts.sum()
        if total == 0:
            return counts * 0.0
        return counts / total * 100.0

    # Overall total column
    total_counts = dfv[cf_col].value_counts().reindex(category_order, fill_value=0)
    total_pct = pct_series(total_counts)

    # Age columns
    age_pcts = {}
    for g in age_order:
        sub = dfv[dfv[age_col] == g]
        c = sub[cf_col].value_counts().reindex(category_order, fill_value=0)
        age_pcts[g] = pct_series(c)

    # Gender columns
    gender_pcts = {}
    for g in gender_order:
        sub = dfv[dfv[gender_col] == g]
        c = sub[cf_col].value_counts().reindex(category_order, fill_value=0)
        gender_pcts[g] = pct_series(c)

    # Ethnicity columns
    eth_pcts = {}
    for g in eth_order:
        sub = dfv[dfv[eth_col] == g]
        c = sub[cf_col].value_counts().reindex(category_order, fill_value=0)
        eth_pcts[g] = pct_series(c)

    # Assemble final wide table
    rows = []
    for cat in category_order:
        row = {"Category": category_labels.get(cat, str(cat))}
        row["Total"] = round(total_pct.loc[cat], pct_decimals)

        for g in age_order:
            row[g] = round(age_pcts[g].loc[cat], pct_decimals)

        for g in gender_order:
            row[g] = round(gender_pcts[g].loc[cat], pct_decimals)

        for g in eth_order:
            row[g] = round(eth_pcts[g].loc[cat], pct_decimals)

        rows.append(row)

    out = pd.DataFrame(rows)

    # Convert to nice % strings (optional)
    for c in out.columns:
        if c != "Category":
            out[c] = out[c].map(lambda x: f"{x:.{pct_decimals}f}%")

    return out
