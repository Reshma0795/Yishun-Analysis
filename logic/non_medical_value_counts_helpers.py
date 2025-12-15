# logic/non_medical_value_counts_helpers.py
import pandas as pd

def build_mapped_value_counts_table(
    df: pd.DataFrame,
    col: str,
    value_map: dict,
    sort_by_order: list = None,
    include_missing: bool = True,
    missing_label: str = "Missing",
):
    """
    Returns a DataFrame:
      Response | Label | Count | Percentage

    - Uses value_map to label coded responses.
    - Keeps unexpected codes (shown as 'Unknown (<code>)')
    - Percentage is out of TOTAL rows in df (including missing), to match your standard.
    """
    if col not in df.columns:
        return pd.DataFrame(columns=["Response", "Label", "Count", "Percentage"])

    s = df[col]
    total_n = len(s)

    vc = s.value_counts(dropna=False)

    rows = []
    for raw, cnt in vc.items():
        if pd.isna(raw):
            resp = missing_label
            label = missing_label
        else:
            # normalize to int if possible
            try:
                raw_int = int(raw) if float(raw).is_integer() else raw
            except Exception:
                raw_int = raw

            resp = raw_int
            if raw_int in value_map:
                label = value_map[raw_int]
            else:
                label = f"Unknown ({raw_int})"

        pct = (cnt / total_n * 100.0) if total_n else 0.0
        rows.append(
            {
                "Response": resp,
                "Label": label,
                "Count": int(cnt),
                "Percentage": f"{pct:.1f}%",
            }
        )

    out = pd.DataFrame(rows)

    if not include_missing:
        out = out[out["Response"] != missing_label].copy()

    # sorting
    if sort_by_order:
        order_index = {v: i for i, v in enumerate(sort_by_order)}
        def _key(x):
            if x == missing_label:
                return (2, 10**9)
            if x in order_index:
                return (0, order_index[x])
            return (1, str(x))
        out["_k"] = out["Response"].apply(_key)
        out = out.sort_values("_k").drop(columns=["_k"]).reset_index(drop=True)

    return out
