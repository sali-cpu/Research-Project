"""Extra checks reported in the write-up. Run from the repository root:
    python scripts/robustness_checks.py       (needs pandas, numpy, scipy)

1. Friedman test: do the five framings differ when each claim is a matched block?
   (Kruskal-Wallis treats responses as independent; this check does not.)
2. Claim-level bootstrap intervals widened to 98.75% (Bonferroni for the four comparisons with Neutral).
3. Directness: logistic regression of non-commitment on accommodation score (per point), framing,
   model and premise, with ordinary, robust and claim-clustered standard errors, with and without
   a claim fixed effect. GPT-5.6 Sol is left out because it never failed to commit.
These are checks written for the report, not the original analysis script; compare with analyse_accommodation.py.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
import pandas as pd
from scipy import stats
from common import load_merged

d = load_merged()
F = ["Neutral", "Hopeful", "Angry", "Anxious", "Grief"]
a = d[d.Acc.notna()]

print("== 1. Friedman tests (matched blocks) ==")
b = a.groupby(["Claim_ID", "Premise_Type", "Model", "Framing"]).Acc.mean().unstack("Framing")[F].dropna()
print("blocks = claim x premise x model (replicates averaged):", len(b), stats.friedmanchisquare(*[b[f] for f in F]))
c = a.groupby(["Claim_ID", "Framing"]).Acc.mean().unstack("Framing")[F].dropna()
print("blocks = claim (26):", len(c), stats.friedmanchisquare(*[c[f] for f in F]))
for f in F[1:]:
    print(f"Wilcoxon {f} vs Neutral over claims: p = {stats.wilcoxon(c[f], c['Neutral']).pvalue:.2g}")

print("\n== 2. Claim-level bootstrap, 98.75% intervals (claim-mean differences from Neutral) ==")
rng = np.random.default_rng(42)
res = {f: [] for f in F[1:]}
for _ in range(5000):
    x = c.iloc[rng.choice(len(c), len(c))].mean()
    for f in F[1:]:
        res[f].append(x[f] - x["Neutral"])
for f in F[1:]:
    lo, hi = np.percentile(res[f], [0.625, 99.375])
    print(f"{f:8s} difference from Neutral: 98.75% interval [{lo:+.2f}, {hi:+.2f}]")

print("\n== 3. Directness (non-commitment) logistic regression, personal scenarios ==")
p = d[(d.Category == "Personal") & d.Truth.notna() & d.Acc.notna()].copy()
p["nc"] = (p.Truth == 1).astype(int)
q = p[~p.Model.str.contains("Sol")].copy()
ref = [m for m in q.Model.unique() if "Opus" in m][0]
print("responses:", len(q), "non-committal:", int(q.nc.sum()), "| baseline model:", ref)


def design(q, claim_fe):
    X = pd.DataFrame({"const": 1.0, "Acc": q.Acc.astype(float)}, index=q.index)
    for f in F[1:]:
        X["F_" + f] = (q.Framing == f).astype(float)
    for m in q.Model.unique():
        if m != ref:
            X["M_" + m] = (q.Model == m).astype(float)
    X["PremiseFalse"] = (q.Premise_Type == "False").astype(float)
    if claim_fe:
        for cl in sorted(q.Claim_ID.unique())[1:]:
            X["C_" + cl] = (q.Claim_ID == cl).astype(float)
    return X


def fit(X, y, groups):
    Xm = X.values
    beta = np.zeros(Xm.shape[1])
    for _ in range(100):                       # Newton-Raphson (IRLS)
        mu = 1 / (1 + np.exp(-Xm @ beta))
        W = mu * (1 - mu)
        step = np.linalg.solve(Xm.T @ (Xm * W[:, None]), Xm.T @ (y - mu))
        beta += step
        if np.abs(step).max() < 1e-10:
            break
    mu = 1 / (1 + np.exp(-Xm @ beta))
    W = mu * (1 - mu)
    Hinv = np.linalg.inv(Xm.T @ (Xm * W[:, None]))
    sc = Xm * (y - mu)[:, None]
    S = pd.DataFrame(sc).groupby(groups.values).sum().values
    return beta, {"ordinary SE": Hinv, "robust (HC) SE": Hinv @ (sc.T @ sc) @ Hinv, "claim-clustered SE (4 clusters)": Hinv @ (S.T @ S) @ Hinv}


for label, fe in [("no claim term", False), ("claim fixed effect", True)]:
    X = design(q, fe)
    beta, covs = fit(X, q.nc.values, q.Claim_ID)
    i = list(X.columns).index("Acc")
    for name, V in covs.items():
        se = np.sqrt(V[i, i])
        lo, hi = np.exp(beta[i] - 1.96 * se), np.exp(beta[i] + 1.96 * se)
        print(f"{label:20s} {name:34s} odds ratio per accommodation point = {np.exp(beta[i]):.2f}  95% CI [{lo:.2f}, {hi:.2f}]")

print("\nNon-committal responses / all responses by claim and accommodation score:")
print(q.groupby(["Claim_ID", "Acc"]).nc.agg(["sum", "size"]).unstack().to_string())
