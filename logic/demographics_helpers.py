# logic/demographics_helpers.py
import pandas as pd


def to_int(x):
    """Safe int conversion. Returns None for missing/unparseable."""
    if pd.isna(x):
        return None
    try:
        return int(x)
    except (TypeError, ValueError):
        return None


def add_age_bins(
    df: pd.DataFrame,
    age_col: str = "Q2",
    out_col: str = "Age_Bin",
    bins=None,
):
    """
    Adds an age bin column.

    Default bins:
      <40, 40–65, 65–85, >=85

    You may pass custom bins like:
      bins = [
        ("<40",  None, 39),
        ("40–65", 40, 65),
        ("65–85", 66, 85),
        (">=85",  86, None),
      ]
    """
    if bins is None:
        bins = [
            ("<40", None, 39),
            ("40–65", 40, 65),
            ("65–85", 66, 85),
            (">=85", 86, None),
        ]

    def bin_age(v):
        v = to_int(v)
        if v is None:
            return None
        for label, lo, hi in bins:
            if lo is None and hi is not None and v <= hi:
                return label
            if lo is not None and hi is not None and lo <= v <= hi:
                return label
            if lo is not None and hi is None and v >= lo:
                return label
        return None

    df = df.copy()
    if age_col not in df.columns:
        df[out_col] = None
        return df

    df[out_col] = df[age_col].apply(bin_age)
    return df


def add_categorical_labels(
    df: pd.DataFrame,
    mappings: dict,
):
    """
    Generic label mapper.

    mappings format:
      {
        "Gender_Label": {"source": "Q4", "map": {1:"Male",2:"Female"}},
        "Ethnicity_Label": {"source":"Q3","map":{1:"Chinese",2:"Malay",3:"Indian",4:"Others"}}
      }
    """
    df = df.copy()
    for out_col, spec in mappings.items():
        source = spec.get("source")
        m = spec.get("map", {})
        if source not in df.columns:
            df[out_col] = None
            continue
        df[out_col] = df[source].apply(lambda x: m.get(to_int(x), None))
    return df
