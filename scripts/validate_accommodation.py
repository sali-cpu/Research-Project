"""
Run this AFTER you've filled in Rater1_Score (all rows) and Rater2_Score
(subsample rows) in Accommodation_Scoring.csv, and merged Rater2's blinded
scores back in by Prompt_ID+Vendor+Tier+Replicate.

Produces two independent pieces of evidence that your Accommodation scoring
isn't "just your opinion":

1. Cohen's Kappa between Rater1 and Rater2 on the reliability subsample
   (human-human agreement).
2. Correlation between your human Accommodation scores and an automated,
   independent signal: the emotion classifier's (1 - P(neutral)) on the
   RESPONSE text — i.e. how much non-neutral emotional content the response
   contains overall (human-automated convergent validity).

SETUP:
    pip install transformers torch pandas scikit-learn scipy

USAGE:
    python validate_accommodation.py

INPUT:  Accommodation_Scoring.csv (with Rater1_Score and Rater2_Score filled in)
OUTPUT: prints Cohen's Kappa and the correlation result to console;
        saves Accommodation_Validated.csv with the emotion-proxy column added.
"""

import pandas as pd
from sklearn.metrics import cohen_kappa_score
from scipy.stats import pearsonr, spearmanr
from transformers import pipeline

INPUT_CSV = "Accommodation_Scoring.csv"
OUTPUT_CSV = "Accommodation_Validated.csv"


def main():
    df = pd.read_csv(INPUT_CSV)

    # --- 1. Cohen's Kappa on the reliability subsample ---
    subsample = df[df["Reliability_Subsample"] == "Y"].copy()
    subsample = subsample.dropna(subset=["Rater1_Score", "Rater2_Score"])
    subsample = subsample[(subsample["Rater1_Score"] != "") & (subsample["Rater2_Score"] != "")]

    if len(subsample) == 0:
        print("No completed subsample rows found — fill in both Rater1_Score and")
        print("Rater2_Score for the Reliability_Subsample='Y' rows before running this.")
    else:
        kappa = cohen_kappa_score(
            subsample["Rater1_Score"].astype(int),
            subsample["Rater2_Score"].astype(int),
            weights="linear",  # appropriate for an ordinal 0-3 scale, not just exact-match
        )
        print(f"=== INTER-RATER RELIABILITY ===")
        print(f"N = {len(subsample)} double-scored responses")
        print(f"Cohen's Kappa (linear-weighted): {kappa:.3f}")
        print("(Typical benchmarks: <0.4 poor, 0.4-0.6 moderate, 0.6-0.8 good, >0.8 excellent)")

    # --- 2. Convergent validity vs. emotion classifier on RESPONSE text ---
    # Keep only rows with a real 0-3 score AND non-empty response text.
    # (EXCLUDED rows and the empty DeepSeek response crashed the classifier.)
    df["Rater1_Score"] = pd.to_numeric(df["Rater1_Score"], errors="coerce")
    df["Response_Text"] = df["Response_Text"].fillna("").astype(str)
    scored_rows = df[df["Rater1_Score"].notna() & (df["Response_Text"].str.strip() != "")].copy()

    if len(scored_rows) == 0:
        print("\nNo Rater1_Score values found yet — fill in Rater1_Score in")
        print("Accommodation_Scoring.csv before running the convergent validity check.")
        print("(Skipping the emotion classifier step for now.)")
        return

    print(f"\nRunning emotion classifier on {len(scored_rows)} scored responses for convergent validity check...")
    classifier = pipeline(
        "text-classification",
        model="j-hartmann/emotion-english-distilroberta-base",
        top_k=None,
    )

    texts = scored_rows["Response_Text"].tolist()
    results = classifier(texts, truncation=True, max_length=512, batch_size=16)

    non_neutral_prob = [
        1 - next((d["score"] for d in r if d["label"] == "neutral"), 0.0)
        for r in results
    ]
    scored_rows["Emotion_NonNeutral_Response"] = non_neutral_prob

    r, p = pearsonr(scored_rows["Rater1_Score"].astype(int), scored_rows["Emotion_NonNeutral_Response"])
    rho, p_s = spearmanr(scored_rows["Rater1_Score"].astype(int), scored_rows["Emotion_NonNeutral_Response"])

    print(f"\n=== CONVERGENT VALIDITY (human score vs. automated emotion signal) ===")
    print(f"N = {len(scored_rows)}")
    print(f"Pearson r = {r:.3f} (p = {p:.4f})")
    print(f"Spearman rho = {rho:.3f} (p = {p_s:.4f})")
    print("A meaningful positive correlation supports that your human Accommodation")
    print("scores track an independent, automated signal of emotional content —")
    print("not just idiosyncratic personal judgement.")

    scored_rows.to_csv(OUTPUT_CSV, index=False)
    print(f"\nSaved -> {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
