# logic/financial_value_counts_helpers.py
import pandas as pd

def build_mapped_value_counts_table(
    df: pd.DataFrame,
    col: str,
    value_label_map: dict,
    include_missing: bool = True,
    missing_label: str = "Missing",
    sort_by_order: list | None = None,
):
    """
    Returns a DataFrame:
      Response | Code | Count | Percentage

    - Uses `value_label_map` to convert codes -> labels.
    - Keeps unknown/unmapped codes as "Other: <code>" so you can spot bad data.
    - Keeps Missing row if include_missing=True
    - Allows you to enforce an order via sort_by_order (list of codes)
    """
    if col not in df.columns:
        return pd.DataFrame(columns=["Response", "Code", "Count", "Percentage"])

    s = df[col]
    total_n = len(s)

    vc = s.value_counts(dropna=False)

    rows = []
    for raw, cnt in vc.items():
        if pd.isna(raw):
            code_out = None
            resp_out = missing_label
        else:
            try:
                code_out = int(raw)
            except Exception:
                code_out = raw

            if code_out in value_label_map:
                resp_out = value_label_map[code_out]
            else:
                resp_out = f"Other: {code_out}"

        pct = (cnt / total_n * 100.0) if total_n else 0.0
        rows.append(
            {
                "Response": resp_out,
                "Code": "" if code_out is None else code_out,
                "Count": int(cnt),
                "Percentage": f"{pct:.1f}%",
            }
        )

    out = pd.DataFrame(rows)

    if not include_missing:
        out = out[out["Response"] != missing_label].copy()

    # Sorting: by provided code order, then everything else, missing last
    if sort_by_order is not None and not out.empty:
        order_index = {c: i for i, c in enumerate(sort_by_order)}

        def _k(row):
            if row["Response"] == missing_label:
                return (3, 10**9)
            code = row["Code"]
            if code in order_index:
                return (0, order_index[code])
            if isinstance(code, int):
                return (1, code)
            return (2, str(code))

        out["_k"] = out.apply(_k, axis=1)
        out = out.sort_values("_k").drop(columns=["_k"]).reset_index(drop=True)

    return out

def impute_q110_to_no(df: pd.DataFrame, col: str = "Q110") -> pd.DataFrame:
    """
    Returns a COPY of df with Q110 imputed:
      3 (Not applicable) -> 2 (No)
      777 (Refused)      -> 2 (No)

    Does not modify the original df.
    """
    df_imp = df.copy()
    if col in df_imp.columns:
        df_imp[col] = df_imp[col].replace({3: 2, 777: 2})
    return df_imp
