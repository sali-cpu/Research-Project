"""Rebuilds the four report figures from data/ and results/. Run from the repository root:
    python scripts/make_figures.py      (needs pandas, numpy, matplotlib)
Output: results/figures/figure1..figure4 (numbering matches the report).
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import pandas as pd, numpy as np, matplotlib
from common import load_merged, ROOT
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
d=load_merged().rename(columns={"Category":"Cat"})
eff=pd.read_csv(ROOT/"results"/"Accommodation_Effects.csv")
OUT=ROOT/"results"/"figures"; OUT.mkdir(parents=True,exist_ok=True)
INK="#0b0b0b"; INK2="#52514e"; GRID="#e4e3df"; BLUE="#2a78d6"; ORANGE="#eb6834"; SURF="#fcfcfb"
plt.rcParams.update({"font.family":"DejaVu Sans","font.size":10,"axes.edgecolor":GRID,"axes.labelcolor":INK2,
  "xtick.color":INK2,"ytick.color":INK2,"text.color":INK,"figure.facecolor":SURF,"axes.facecolor":SURF,
  "axes.spines.top":False,"axes.spines.right":False,"axes.titleweight":"bold","axes.titlesize":11,"axes.titlelocation":"left"})
FR=["Neutral","Hopeful","Angry","Anxious","Grief"]
NAME={"Anthropic Haiku":"Claude Haiku 4.5","Anthropic Opus":"Claude Opus 5","Groq GPT-OSS-120B":"gpt-oss-120b",
 "DeepSeek Flash":"DeepSeek V4 Flash","DeepSeek Pro":"DeepSeek V4 Pro","OpenAI Luna":"GPT-5.6 Luna","OpenAI Sol":"GPT-5.6 Sol"}
a=d[d.Acc.notna()].copy(); a["M"]=a.Model.map(NAME)

# Figure 1: increase over Neutral, dot + whisker
e=eff[(eff.Group=="All models")&(eff.Contrast.isin(FR[1:]))].set_index("Contrast").loc[FR[1:]]
fig,ax=plt.subplots(figsize=(7,3.4),dpi=200)
y=np.arange(len(e))[::-1]
ax.axvline(0,color=INK2,lw=1)
ax.hlines(y,e.CI_low,e.CI_high,color=BLUE,lw=2)
ax.plot(e.Estimate,y,"o",ms=7,color=BLUE,mec=SURF,mew=1.2)
for yi,(k,r) in zip(y,e.iterrows()):
    ax.text(r.CI_high+0.03,yi,f"+{r.Estimate:.2f}",va="center",color=INK,fontsize=10)
ax.set_yticks(y); ax.set_yticklabels(e.index)
ax.set_xlim(-0.05,1.45); ax.set_xlabel("Increase in mean accommodation score (0 to 3) compared with Neutral")
ax.xaxis.grid(True,color=GRID,lw=.8); ax.set_axisbelow(True); ax.tick_params(length=0)
ax.set_title("Stated emotion raises emotional accommodation, in a clear order")
fig.text(0.01,0.01,"Dots show the estimate; lines show 95% intervals from resampling the 26 claims (5,000 resamples). N = 5,427 responses.",fontsize=7.5,color=INK2)
fig.tight_layout(rect=(0,0.04,1,1)); fig.savefig(OUT/"figure1_framing_effect.png"); plt.close()

# Figure 2: heatmap model x framing
pv=a.pivot_table(index="M",columns="Framing",values="Acc")[FR]
pv=pv.sort_values("Grief",ascending=False)
cm=LinearSegmentedColormap.from_list("b",["#f1f6fd","#2a78d6","#123c7a"])
fig,ax=plt.subplots(figsize=(7,3.9),dpi=200)
im=ax.imshow(pv.values,cmap=cm,vmin=0,vmax=2.0,aspect="auto")
for i in range(pv.shape[0]):
    for j in range(pv.shape[1]):
        v=pv.values[i,j]; ax.text(j,i,f"{v:.2f}",ha="center",va="center",fontsize=9.5,color="white" if v>=0.9 else INK)
ax.set_xticks(range(5)); ax.set_xticklabels(FR); ax.set_yticks(range(len(pv))); ax.set_yticklabels(pv.index)
ax.xaxis.tick_top(); ax.tick_params(length=0)
for s in ax.spines.values(): s.set_visible(False)
ax.set_xticks(np.arange(-.5,5,1),minor=True); ax.set_yticks(np.arange(-.5,len(pv),1),minor=True)
ax.grid(which="minor",color=SURF,lw=2); ax.tick_params(which="minor",length=0)
fig.suptitle("Models differ widely in how much they accommodate",x=0.01,ha="left",fontweight="bold",fontsize=11,y=0.99)
fig.text(0.01,0.015,"Cell = mean accommodation score (0 to 3). Darker means more accommodation. Rows ordered by Grief score.",fontsize=7.5,color=INK2)
fig.tight_layout(rect=(0,0.04,1,0.95)); fig.savefig(OUT/"figure2_model_by_framing.png"); plt.close()

# Figure 4 in the report: non-commitment (directness)
p=d[(d.Cat=="Personal")&d.Truth.notna()].copy(); p["nc"]=(p.Truth==1)
fig,(ax1,ax2)=plt.subplots(1,2,figsize=(8.4,3.7),dpi=200,gridspec_kw={"width_ratios":[5,3.3]},sharey=True)
g=p.groupby("Framing").nc.agg(["mean","size"]).loc[FR]
ax1.bar(range(5),g["mean"]*100,color=BLUE,width=.58)
for i,(m,n) in enumerate(zip(g["mean"],g["size"])):
    ax1.text(i,m*100+0.7,f"{m*100:.1f}%",ha="center",fontsize=9,color=INK)
ax1.set_xticks(range(5)); ax1.set_xticklabels([f"{f}\nn={n}" for f,n in zip(FR,g["size"])],fontsize=8.5)
ax1.set_title("By emotional framing"); ax1.set_ylabel("Responses that did not commit (%)")
pa=p[p.Acc.isin([0,1,2])]
g2=pa.groupby("Acc").nc.agg(["mean","size"])
ax2.bar(range(3),g2["mean"]*100,color=BLUE,width=.58)
for i,(m,n) in enumerate(zip(g2["mean"],g2["size"])):
    ax2.text(i,m*100+0.7,f"{m*100:.1f}%",ha="center",fontsize=9,color=INK)
ax2.set_xticks(range(3)); ax2.set_xticklabels([f"Score {int(k)}\nn={n}" for k,n in zip(g2.index,g2["size"])],fontsize=8.5)
ax2.set_title("By accommodation score")
for ax in (ax1,ax2):
    ax.yaxis.grid(True,color=GRID,lw=.8); ax.set_axisbelow(True); ax.tick_params(length=0); ax.set_ylim(0,40)
fig.suptitle("Less direct answers rise under Anxious and Grief framing and with more accommodation",x=0.01,ha="left",fontweight="bold",fontsize=10.5,y=0.99)
fig.text(0.01,0.012,"Four personal scenarios, 839 responses. One response scored 3 is not shown. Exploratory: four scenarios only.",fontsize=7.5,color=INK2)
fig.tight_layout(rect=(0,0.04,1,0.93)); fig.savefig(OUT/"figure4_directness.png"); plt.close()

# Figure 3 in the report: true vs false premise
t=a.groupby(["Framing","Premise_Type"]).Acc.mean().unstack()[["True","False"]].loc[FR]
fig,ax=plt.subplots(figsize=(7,3.5),dpi=200)
x=np.arange(5)
dx=0.09
ax.plot(x-dx,t["True"],"o",ms=9,color=BLUE,mec=SURF,mew=1.2,zorder=3,label="True claim")
ax.plot(x+dx,t["False"],"o",ms=9,color=ORANGE,mec=SURF,mew=1.2,zorder=3,label="False claim")
ax.set_xticks(x); ax.set_xticklabels(FR); ax.set_ylabel("Mean accommodation (0 to 3)")
ax.yaxis.grid(True,color=GRID,lw=.8); ax.set_axisbelow(True); ax.tick_params(length=0); ax.set_ylim(0,1.3)
ax.legend(frameon=False,loc="upper left",ncol=2,fontsize=9)
ax.set_title("Accommodation differs little between true and false claims")
fig.text(0.01,0.01,"Overall false minus true: -0.045 (95% interval -0.096 to +0.005), so no clear difference. N = 5,427 responses.",fontsize=7.5,color=INK2)
fig.tight_layout(rect=(0,0.04,1,1)); fig.savefig(OUT/"figure3_true_vs_false.png"); plt.close()
print(t.round(3)); print(pv.round(2))
