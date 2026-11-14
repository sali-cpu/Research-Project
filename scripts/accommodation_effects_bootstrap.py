"""
Effect sizes for Accommodation with claim-level cluster-bootstrap 95% CIs.
Resamples the 26 claims (not rows), so repeated use of the same claim across
models/replicates/framings is respected.

Run:  python accommodation_effects_bootstrap.py
Needs: pandas, numpy  (Accommodation_Analysis_Ready.csv from analyse_accommodation.py)
Output: Accommodation_Effects.csv + printed tables
"""
import numpy as np
import pandas as pd

rng = np.random.default_rng(42)
B = 5000
d = pd.read_csv("Accommodation_Analysis_Ready.csv")
d["Premise_Type"] = d["Premise_Type"].astype(str)
claims = d["Claim_ID"].unique()
by_claim = {c: g for c, g in d.groupby("Claim_ID")}


def boot(stat):
    """stat(df) -> float. Returns point estimate and 95% cluster-bootstrap CI."""
    est = stat(d)
    vals = []
    for _ in range(B):
        samp = rng.choice(claims, size=len(claims), replace=True)
        vals.append(stat(pd.concat([by_claim[c] for c in samp])))
    vals = np.array(vals)
    return est, np.nanpercentile(vals, 2.5), np.nanpercentile(vals, 97.5)


def diff(df, f1, f2, model=None):
    x = df if model is None else df[df["Model"] == model]
    return x.loc[x["Framing"] == f1, "Acc"].mean() - x.loc[x["Framing"] == f2, "Acc"].mean()


rows = []
print("=== Mean Accommodation difference vs Neutral (all models pooled) ===")
for f in ["Hopeful", "Angry", "Anxious", "Grief"]:
    e, lo, hi = boot(lambda x, f=f: diff(x, f, "Neutral"))
    rows.append(("All models", f, e, lo, hi))
    print(f"{f:8s} {e:+.2f}  [{lo:+.2f}, {hi:+.2f}]")

print("\n=== Grief minus Neutral, per model ===")
for m in sorted(d["Model"].unique()):
    e, lo, hi = boot(lambda x, m=m: diff(x, "Grief", "Neutral", m))
    rows.append((m, "Grief", e, lo, hi))
    print(f"{m:20s} {e:+.2f}  [{lo:+.2f}, {hi:+.2f}]")

print("\n=== Anxious minus Neutral, per model ===")
for m in sorted(d["Model"].unique()):
    e, lo, hi = boot(lambda x, m=m: diff(x, "Anxious", "Neutral", m))
    rows.append((m, "Anxious", e, lo, hi))
    print(f"{m:20s} {e:+.2f}  [{lo:+.2f}, {hi:+.2f}]")

print("\n=== Premise effect: False minus True (mean Accommodation), non-Neutral ===")
nn_stat = lambda x: (x[(x.Framing != "Neutral") & (x.Premise_Type == "False")]["Acc"].mean()
                     - x[(x.Framing != "Neutral") & (x.Premise_Type == "True")]["Acc"].mean())
e, lo, hi = boot(nn_stat)
rows.append(("All models", "False-True", e, lo, hi))
print(f"{e:+.3f}  [{lo:+.3f}, {hi:+.3f}]   (CI containing 0 = no premise effect)")

pd.DataFrame(rows, columns=["Group", "Contrast", "Estimate", "CI_low", "CI_high"]).to_csv(
    "Accommodation_Effects.csv", index=False)
print("\nSaved -> Accommodation_Effects.csv")
