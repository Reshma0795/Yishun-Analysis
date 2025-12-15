# logic/value_counts_helpers.py
import pandas as pd

def build_value_counts_table(
    df: pd.DataFrame,
    col: str,
    include_missing: bool = True,
    sort_numeric: bool = True,
    missing_label: str = "Missing",
):
    """
    Returns a DataFrame:
      Response | Count | Percentage

    - Keeps 777/999/etc automatically (since we do NOT recode)
    - Includes Missing row if include_missing=True
    - Does NOT drop anything unless you ask it to
    """
    if col not in df.columns:
        return pd.DataFrame(columns=["Response", "Count", "Percentage"])

    s = df[col]
    total_n = len(s)

    vc = s.value_counts(dropna=False)

    rows = []
    for resp, cnt in vc.items():
        if pd.isna(resp):
            resp_out = missing_label
        else:
            # keep ints clean if possible (777 instead of 777.0)
            try:
                resp_out = int(resp) if float(resp).is_integer() else resp
            except Exception:
                resp_out = resp

        pct = (cnt / total_n * 100.0) if total_n else 0.0
        rows.append({"Response": resp_out, "Count": int(cnt), "Percentage": f"{pct:.1f}%"})

    out = pd.DataFrame(rows)

    if not include_missing:
        out = out[out["Response"] != missing_label].copy()

    if sort_numeric and not out.empty:
        def sort_key(x):
            if x == missing_label:
                return (2, 10**9)
            try:
                return (0, int(x))
            except Exception:
                return (1, str(x))

        out["_k"] = out["Response"].apply(sort_key)
        out = out.sort_values("_k").drop(columns=["_k"]).reset_index(drop=True)

    return out


# ============================================================
# Descriptive stats helpers (numeric)
# ============================================================

DEFAULT_INVALID_CODES = {777, 888, 999}

def _coerce_numeric_series(
    df: pd.DataFrame,
    col: str,
    invalid_codes=DEFAULT_INVALID_CODES,
):
    """
    Returns:
      s_raw  : original series
      s_num  : numeric series (coerced), invalid_codes -> NA
      s_valid: numeric series with NA dropped
    """
    if col not in df.columns:
        empty = pd.Series([], dtype="float64")
        return empty, empty, empty

    s_raw = df[col]
    s_num = pd.to_numeric(s_raw, errors="coerce")

    if invalid_codes:
        s_num = s_num.mask(s_num.isin(list(invalid_codes)))

    s_valid = s_num.dropna()
    return s_raw, s_num, s_valid


def build_descriptive_stats_table(
    df: pd.DataFrame,
    col: str,
    invalid_codes=DEFAULT_INVALID_CODES,
):
    """
    Returns a 1-row DataFrame with common descriptive statistics.
    Invalid codes (777/888/999) are excluded from stats by default.
    """
    s_raw, s_num, s_valid = _coerce_numeric_series(df, col, invalid_codes=invalid_codes)

    total_n = int(len(s_raw))
    missing_n = int(s_num.isna().sum())
    valid_n = int(s_valid.shape[0])

    if valid_n == 0:
        return pd.DataFrame([{
            "Total N": total_n,
            "Valid N": 0,
            "Missing/Invalid N": total_n,
            "Mean": None,
            "Median": None,
            "Std": None,
            "Min": None,
            "P25": None,
            "P75": None,
            "Max": None,
        }])

    desc = s_valid.describe(percentiles=[0.25, 0.75])

    return pd.DataFrame([{
        "Total N": total_n,
        "Mean": round(float(desc["mean"]), 2),
        "Median": round(float(s_valid.median()), 2),
        "Std": round(float(desc["std"]), 2) if pd.notna(desc["std"]) else None,
        "Min": float(desc["min"]),
        "P25": float(desc["25%"]),
        "P75": float(desc["75%"]),
        "Max": float(desc["max"]),
    }])


def build_numeric_distribution_table(
    df: pd.DataFrame,
    col: str,
    invalid_codes=DEFAULT_INVALID_CODES,
):
    """
    Distribution of numeric values AFTER excluding invalid codes.
    Returns: Value | Count | Percentage
    """
    _, _, s_valid = _coerce_numeric_series(df, col, invalid_codes=invalid_codes)
    if s_valid.empty:
        return pd.DataFrame(columns=["Value", "Count", "Percentage"])

    total = int(len(s_valid))
    vc = s_valid.value_counts(dropna=False).sort_index()

    out = pd.DataFrame({
        "Value": vc.index.map(lambda x: int(x) if pd.notna(x) and float(x).is_integer() else x),
        "Count": vc.values.astype(int),
    })

    out["Percentage"] = out["Count"].apply(lambda c: f"{(c/total*100.0):.1f}%")
    return out.reset_index(drop=True)
