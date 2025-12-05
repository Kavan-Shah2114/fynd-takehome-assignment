# app/shared/data_io.py

import pandas as pd
import os
from pathlib import Path

DATA_DIR = Path("data")
DEFAULT_PRIMARY = DATA_DIR / "yelp_reviews.csv"
DEFAULT_FALLBACK = DATA_DIR / "sample_yelp.csv"

def _normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    # normalize common column names to 'review_text' and 'true_stars'
    cols = {c: c for c in df.columns}
    for c in df.columns:
        lc = c.lower()
        if lc in ("text", "review", "review_text", "content"):
            cols[c] = "review_text"
        if lc in ("stars", "rating", "true_stars"):
            cols[c] = "true_stars"

    df = df.rename(columns=cols)

    # ensure review_text column exists
    if "review_text" not in df.columns:
        # try to find any string column
        for c in df.columns:
            if df[c].dtype == object:
                df = df.rename(columns={c: "review_text"})
                break

    # ensure true_stars exists (if missing, fill with -1)
    if "true_stars" not in df.columns:
        df["true_stars"] = -1

    return df[["review_text", "true_stars"]].dropna(subset=["review_text"]).reset_index(drop=True)

def load_dataset(primary_path: str = None, fallback_path: str = None) -> pd.DataFrame:
    """
    Loads dataset, preferring primary_path (data/yelp_reviews.csv),
    falling back to fallback_path (data/sample_yelp.csv).
    Normalizes columns and returns DataFrame with ['review_text','true_stars'].
    """

    p1 = Path(primary_path) if primary_path else DEFAULT_PRIMARY
    p2 = Path(fallback_path) if fallback_path else DEFAULT_FALLBACK

    if p1.exists():
        df = pd.read_csv(p1)
    elif p2.exists():
        df = pd.read_csv(p2)
    else:
        raise FileNotFoundError(
            f"Neither dataset found:\n - {p1}\n - {p2}\nPlease place yelp_reviews.csv or sample_yelp.csv in data/ folder."
        )

    return _normalize_df(df)

def load_sample_yelp(path="data/sample_yelp.csv"):
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Dataset not found at: {path}")
    df = pd.read_csv(p)
    return _normalize_df(df)