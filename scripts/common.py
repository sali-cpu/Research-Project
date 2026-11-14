"""Shared loader: merges the three data files into one table used by make_figures.py and robustness_checks.py.

Run from the repository root, e.g.  python scripts/make_figures.py
"""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
KEY = ["Prompt_ID", "Vendor", "Tier", "Replicate"]
PERSONAL_CLAIMS = ["C23", "C24", "C25", "C26"]   # the four personal ("Applied") scenarios


def load_merged():
    main = pd.read_csv(ROOT / "data" / "Analysis_Scored_Final.csv")
    acc = pd.read_csv(ROOT / "data" / "Accommodation_Scoring.csv")
    man = pd.read_csv(ROOT / "data" / "Truthfulness_Review.csv", dtype=str, keep_default_na=False)
    for d in (main, acc, man):
        d["Replicate"] = d["Replicate"].astype(int)
    d = main.merge(acc[KEY + ["Rater1_Score"]], on=KEY, validate="1:1")
    d = d.merge(man[KEY + ["Truthfulness_Manual"]], on=KEY, how="left")
    d["Premise_Type"] = d["Premise_Type"].astype(str)
    d["Model"] = d["Vendor"] + " " + d["Tier"]
    d["Category"] = np.where(d["Claim_ID"].isin(PERSONAL_CLAIMS), "Personal", "Trivia")
    # Truthfulness: the manual review score where one exists, otherwise the automated score.
    d["Truth"] = pd.to_numeric(d["Truthfulness_Manual"], errors="coerce").fillna(
        pd.to_numeric(d["Truthfulness_Auto"], errors="coerce"))
    # Accommodation: human score 0-3 (rows marked EXCLUDED become missing).
    d["Acc"] = pd.to_numeric(d["Rater1_Score"], errors="coerce")
    return d
