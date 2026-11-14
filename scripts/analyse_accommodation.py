"""
Accommodation analysis (descriptives + regressions).

Inputs (same folder):  Accommodation_Scoring.csv, Analysis_Scored_Final.csv
Outputs: Accommodation_Analysis_Ready.csv + printed tables

Requires: pip install pandas scipy statsmodels
NOTE: the descriptive tables were run and checked. The statsmodels models
below were NOT executed by me (no statsmodels in my sandbox) - if one errors,
paste me the traceback.
"""
import numpy as np
import pandas as pd
from scipy import stats

KEY = ["Prompt_ID", "Vendor", "Tier", "Replicate"]

acc = pd.read_csv("Accommodation_Scoring.csv")
main = pd.read_csv("Analysis_Scored_Final.csv")
df = main.merge(acc[KEY + ["Rater1_Score"]], on=KEY, validate="1:1")
df["Premise_Type"] = df["Premise_Type"].astype(str)   # pandas turns True/False into bools
df["Model"] = df["Vendor"] + " " + df["Tier"]
df["Category"] = np.where(df["Claim_ID"].isin(["C23", "C24", "C25", "C26"]), "Applied", "Trivia")

excluded = df[df["Rater1_Score"] == "EXCLUDED"]
d = df[df["Rater1_Score"] != "EXCLUDED"].copy()
d["Acc"] = d["Rater1_Score"].astype(int)
d.to_csv("Accommodation_Analysis_Ready.csv", index=False)

print(f"Scored rows: {len(d)}   Excluded: {len(excluded)}")
print("\nExcluded by model:\n", excluded["Model"].value_counts().to_string())
print("\nExcluded by framing:\n", excluded["Framing"].value_counts().to_string())

print("\n=== Mean Accommodation by Framing ===")
print(d.groupby("Framing")["Acc"].agg(["mean", "count"]).round(3))
print("\n=== Score distribution by Framing (row %) ===")
print((pd.crosstab(d["Framing"], d["Acc"], normalize="index") * 100).round(1))
print("\n=== Mean Accommodation: Model x Framing ===")
print(d.pivot_table(index="Model", columns="Framing", values="Acc").round(2))
print("\n=== Mean Accommodation: Premise x Framing ===")
print(d.pivot_table(index="Framing", columns="Premise_Type", values="Acc").round(3))

print("\n=== Omnibus tests (framing) ===")
print("Kruskal-Wallis:", stats.kruskal(*[g["Acc"].values for _, g in d.groupby("Framing")]))

# ---- Regressions (SEs clustered by claim, because 26 claims are reused) ----
import statsmodels.formula.api as smf
from statsmodels.miscmodels.ordinal_model import OrderedModel

# 1) Ordinal (proportional-odds) logit on the 0-3 scale, NON-neutral framings only
#    (Neutral is ~0 everywhere, which causes quasi-separation).
nn = d[d["Framing"] != "Neutral"].copy()
X = pd.get_dummies(nn[["Framing", "Model"]], drop_first=False).astype(float)
X = X.drop(columns=["Framing_Hopeful", "Model_OpenAI Sol"])
X["False_premise"] = (nn["Premise_Type"] == "False").astype(float)
try:
    om = OrderedModel(nn["Acc"], X, distr="logit").fit(
        method="bfgs", disp=False, cov_type="cluster",
        cov_kwds={"groups": pd.factorize(nn["Claim_ID"])[0]})
    print("\n=== Ordinal logit, Accommodation 0-3 (ref: Hopeful, OpenAI Sol) ===")
    res = pd.DataFrame({"OR": np.exp(om.params), "p": om.pvalues}).loc[X.columns]
    print(res.round(4))
except Exception as e:
    print("\nOrdinal model failed:", e)

# 2) Binary logit fallback: P(Acc >= 1), clustered by claim
nn["acc_any"] = (nn["Acc"] >= 1).astype(int)
m = smf.logit("acc_any ~ C(Framing, Treatment('Hopeful')) + C(Model, Treatment('OpenAI Sol')) + C(Premise_Type)",
              data=nn).fit(disp=False, cov_type="cluster",
                           cov_kwds={"groups": pd.factorize(nn["Claim_ID"])[0]})
print("\n=== Logit P(Accommodation>=1), non-Neutral ===")
print(pd.DataFrame({"OR": np.exp(m.params), "p": m.pvalues}).round(4))
