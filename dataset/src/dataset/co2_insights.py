"""
Insight plots for the cleaned World Bank CO2 dataset.

  A. Regional small multiples   - how each region's emissions moved vs 1990
  B. Slope chart                - who got better / worse on CO2 damage (% of GNI), 1990 -> 2021
  C. Heatmap                    - when growth accelerated or reversed, country x year
  D. Rank (bump) chart          - how the top 10 countries by CO2 damage reshuffled
  E. Scatter                    - does a heavier carbon burden go with more firms monitoring CO2?
  F. World map (optional)       - % change since 1990, banded; needs `pip install plotly`

Usage:
    python co2_insights.py path/to/Visualization-ready_CO2_dataset.csv [output_dir]
"""

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.colors import BoundaryNorm, ListedColormap
import numpy as np
import pandas as pd

CSV = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("Visualization-ready_CO2_dataset.csv")
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("co2_insights")
OUT.mkdir(parents=True, exist_ok=True)

IND = {"pct1990": "EN.GHG.CO2.ZG.AR5", "damage_usd": "NY.ADJ.DCO2.CD",
       "damage_gni": "NY.ADJ.DCO2.GN.ZS", "firms": "IC.FRM.CO2.ZS"}

AGGREGATES = {
    "AFE", "AFW", "ARB", "CEB", "CSS", "EAP", "EAR", "EAS", "ECA", "ECS", "EMU",
    "EUU", "FCS", "HIC", "HPC", "IBD", "IBT", "IDA", "IDB", "IDX", "LAC", "LCN",
    "LDC", "LIC", "LMC", "LMY", "LTE", "MEA", "MIC", "MNA", "NAC", "OED", "OSS",
    "PRE", "PSS", "PST", "SAS", "SSA", "SSF", "SST", "TEA", "TEC", "TLA", "TMN",
    "TSA", "TSS", "UMC", "WLD",
}

C = {"blue": "#257de0", "orange": "#f47230", "aqua": "#00b894", "red": "#ec4647",
     "text": "#191919", "muted": "#666666", "faint": "#c8c8c8", "grid": "#e6e6e6"}
CAT = ["#257de0", "#f47230", "#00b894", "#f2a600", "#ee7fac", "#008a17",
       "#6a4ce2", "#ec4647"]

plt.rcParams.update({
    "figure.dpi": 110, "savefig.dpi": 200, "savefig.bbox": "tight",
    "font.size": 10, "axes.titlesize": 13, "axes.titleweight": "bold",
    "axes.titlelocation": "left", "axes.titlepad": 24, "axes.edgecolor": C["grid"],
    "axes.labelcolor": C["muted"], "xtick.color": C["muted"], "ytick.color": C["muted"],
    "axes.grid": True, "grid.color": C["grid"], "grid.linewidth": 0.8,
    "axes.spines.top": False, "axes.spines.right": False, "axes.axisbelow": True,
    "text.color": C["text"], "legend.frameon": False,
})


def note(ax, text):
    ax.text(0, 1.015, text, transform=ax.transAxes, fontsize=9,
            color=C["muted"], va="bottom")


def save(fig, name):
    fig.savefig(OUT / name)
    plt.close(fig)
    print("saved", OUT / name)


df = pd.read_csv(CSV)
is_agg = df["Country Code"].isin(AGGREGATES)
countries, aggregates = df[~is_agg], df[is_agg]


def wide(frame, key):
    """Country x Year table for one indicator."""
    s = frame[frame["Indicator Code"] == IND[key]]
    return s.pivot_table(index="Country Name", columns="Year", values="Value")


pct = wide(countries, "pct1990")
usd = wide(countries, "damage_usd")
gni = wide(countries, "damage_gni")
DAMAGE_END = 2021  # damage series stop here


# ---------------------------------------------- A. regional small multiples --
regions = {"EAS": "East Asia & Pacific", "SAS": "South Asia",
           "MEA": "Middle East, N. Africa,\nAfghanistan & Pakistan",
           "SSF": "Sub-Saharan Africa", "LCN": "Latin America & Caribbean",
           "NAC": "North America", "ECS": "Europe & Central Asia"}
reg = (aggregates[aggregates["Indicator Code"] == IND["pct1990"]]
       .pivot_table(index="Year", columns="Country Code", values="Value"))
reg = reg[[c for c in regions if c in reg.columns]]
world = (aggregates.query("`Country Code` == 'WLD'")
         .loc[lambda d: d["Indicator Code"] == IND["pct1990"]]
         .set_index("Year")["Value"])

fig, axes = plt.subplots(2, 4, figsize=(13, 6.5), sharex=True, sharey=True)
order = reg.iloc[-1].sort_values(ascending=False).index  # highest growth first
for ax, code in zip(axes.flat, order):
    for other in reg.columns:                       # all regions as faint context
        ax.plot(reg.index, reg[other], color=C["faint"], lw=0.8)
    ax.plot(world.index, world, color=C["muted"], lw=1, ls="--")
    ax.plot(reg.index, reg[code], color=C["blue"], lw=2.4)
    ax.axhline(0, color=C["muted"], lw=0.8)
    last = reg[code].dropna()
    ax.set_title(f"{regions[code]}\n{last.iloc[-1]:+.0f}% by {last.index[-1]}",
                 fontsize=10, pad=6)
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(decimals=0))
axes.flat[-1].axis("off")
axes.flat[-1].text(0, 0.5, "Blue: the region\nGrey: other regions\n"
                   "Dashed: world", fontsize=10, color=C["muted"], va="center",
                   transform=axes.flat[-1].transAxes)
fig.suptitle("CO₂ emissions vs 1990, by region", x=0.06, ha="left",
             fontsize=14, fontweight="bold")
fig.text(0.06, 0.925, "Same y-axis in every panel, so heights compare directly",
         fontsize=9.5, color=C["muted"])
fig.tight_layout(rect=(0, 0, 1, 0.92))
save(fig, "A_regions_small_multiples.png")


# ---------------------------------------------------------- B. slope chart --
# Largest economies by 2021 damage, compared on the burden measure (% of GNI)
start = 1995  # 1990 is missing for many ex-Soviet states; 1995 has fuller coverage
big = usd[DAMAGE_END].nlargest(25).index
slope = gni.loc[gni.index.isin(big), [start, DAMAGE_END]].dropna()
slope = slope.loc[(slope[DAMAGE_END] - slope[start]).abs().nlargest(12).index]

fig, ax = plt.subplots(figsize=(7.5, 8))
def spread(values, gap, iters=200):
    """Nudge label positions apart (at least `gap`) while staying near their dots."""
    pos = np.array(values, dtype=float)
    for _ in range(iters):
        order = np.argsort(pos)
        moved = False
        for i, j in zip(order[:-1], order[1:]):
            overlap = gap - (pos[j] - pos[i])
            if overlap > 0:
                pos[i] -= overlap / 2
                pos[j] += overlap / 2
                moved = True
        if not moved:
            break
    return pos


gap = (slope.values.max() - slope.values.min()) * 0.03
left_y, right_y = spread(slope[start].values, gap), spread(slope[DAMAGE_END].values, gap)
for (name, (a, b)), ly, ry in zip(slope.iterrows(), left_y, right_y):
    col = C["red"] if b > a else C["blue"]
    ax.plot([0, 1], [a, b], color=col, lw=2, marker="o", ms=6)
    ax.text(-0.04, ly, f"{name} {a:.1f}%", ha="right", va="center", fontsize=8.5)
    ax.text(1.04, ry, f"{b:.1f}% {name}", ha="left", va="center", fontsize=8.5)
ax.set_xticks([0, 1], [str(start), str(DAMAGE_END)])
ax.set_xlim(-0.9, 1.9)
ax.yaxis.set_visible(False)
ax.grid(False)
ax.spines[["left", "bottom"]].set_visible(False)
ax.set_title(f"CO₂ damage as % of GNI, {start} → {DAMAGE_END}")
note(ax, "12 biggest movers among the 25 largest emitters · red = heavier burden, blue = lighter")
save(fig, "B_slope_damage_gni.png")


# ------------------------------------------------------------- C. heatmap --
top30 = usd[DAMAGE_END].nlargest(30).index   # biggest emitters by damage
hm = pct.loc[pct.index.isin(top30)]
hm = hm.loc[hm[hm.columns.max()].sort_values(ascending=False).index]

bounds = [-100, -50, -25, 0, 50, 100, 200, 400, 1000, 1e6]
colors = ["#1757ac", "#519ced", "#b6d5f8",                 # falls: blues
          "#fde0d6", "#f8b4a0", "#f2876b", "#e4573e", "#c23324", "#8f1d14"]
cmap, norm = ListedColormap(colors), BoundaryNorm(bounds, len(colors))

fig, ax = plt.subplots(figsize=(13, 9))
im = ax.imshow(hm.values, aspect="auto", cmap=cmap, norm=norm,
               interpolation="nearest")
ax.set_yticks(range(len(hm)), hm.index, fontsize=9)
yrs = hm.columns.tolist()
ticks = [i for i, y in enumerate(yrs) if y % 5 == 0]
ax.set_xticks(ticks, [yrs[i] for i in ticks])
ax.grid(False)
cb = fig.colorbar(im, ax=ax, ticks=bounds[:-1], fraction=0.03, pad=0.02)
cb.ax.set_yticklabels([f"{b:,.0f}%" for b in bounds[:-1]])
cb.set_label("% change from 1990")
ax.set_title("CO₂ emissions vs 1990 — 30 largest emitters")
note(ax, "Sorted by latest value · banded colours keep extreme growers from washing out the rest")
save(fig, "C_heatmap_pct_change.png")


# ------------------------------------------------------- D. bump/rank chart --
years = list(range(1990, DAMAGE_END + 1))
ranks = usd[years].rank(ascending=False)
top10 = ranks[DAMAGE_END].nsmallest(10).index
# Also keep anyone who was top 5 in 1990 but fell out, to show the reshuffle
dropped = ranks[1990].nsmallest(5).index.difference(top10)
show = list(top10) + list(dropped)

fig, ax = plt.subplots(figsize=(11, 6.5))
for i, name in enumerate(show):
    r = ranks.loc[name, years]
    col = CAT[i] if i < len(CAT) else (C["muted"] if name in top10 else C["faint"])
    ax.plot(years, r, color=col, lw=2.2, marker="o", ms=3, clip_on=True)
    ax.text(years[-1] + 0.4, r.iloc[-1], name, va="center", fontsize=9)
    if r.iloc[0] <= 15:  # only label starting ranks that are on the chart
        ax.text(years[0] - 0.4, r.iloc[0], name, va="center", ha="right",
                fontsize=8, color=C["muted"])
ax.invert_yaxis()
ax.set_ylim(15.5, 0.5)
ax.set_yticks(range(1, 16))
ax.set_xlim(1985, 2026)
ax.set_ylabel("Rank by CO₂ damage (US$)")
ax.set_title(f"Who causes the most CO₂ damage? Ranking, 1990–{DAMAGE_END}")
note(ax, "Top 10 in 2021 (ranks 9–10 in grey, faint = was top 5 in 1990 but fell out) · lines leaving the bottom were ranked below 15")
save(fig, "D_rank_damage_usd.png")


# --------------------------------------------------------------- E. scatter --
firms = (countries[countries["Indicator Code"] == IND["firms"]]
         .sort_values("Year").groupby("Country Name").tail(1)
         .set_index("Country Name")["Value"])
sc = pd.DataFrame({"burden": gni[DAMAGE_END], "firms": firms}).dropna()

fig, ax = plt.subplots(figsize=(9, 6.5))
ax.scatter(sc["burden"], sc["firms"], s=40, color=C["blue"], alpha=0.75,
           edgecolor="white", linewidth=1)
ax.set_xscale("log")
pct_fmt = mticker.FuncFormatter(lambda v, _: f"{v:g}%")
ax.xaxis.set_major_formatter(pct_fmt)
ax.xaxis.set_minor_formatter(mticker.FuncFormatter(
    lambda v, _: f"{v:g}%" if f"{v:g}".lstrip("0.")[:1] in ("2", "5") else ""))
ax.yaxis.set_major_formatter(mticker.PercentFormatter(decimals=0))
# Trend on log(x), plus correlation, so the reader sees how weak/strong it is
x, y = np.log10(sc["burden"]), sc["firms"]
m, b = np.polyfit(x, y, 1)
xs = np.linspace(x.min(), x.max(), 50)
ax.plot(10 ** xs, m * xs + b, color=C["orange"], lw=2)
r = np.corrcoef(x, y)[0, 1]
for name in pd.concat([sc["firms"].nlargest(4), sc["burden"].nlargest(4)]).index.unique():
    ax.annotate(name, (sc.loc[name, "burden"], sc.loc[name, "firms"]),
                xytext=(5, 3), textcoords="offset points", fontsize=8, color=C["muted"])
ax.set_xlabel(f"CO₂ damage, % of GNI ({DAMAGE_END}, log scale)")
ax.set_ylabel("Firms monitoring own CO₂ (latest survey)")
ax.set_title("Heavier carbon burden vs firms tracking emissions")
note(ax, f"{len(sc)} countries · r = {r:.2f} · exploratory: survey years (2021–25) differ from {DAMAGE_END}")
save(fig, "E_scatter_burden_vs_firms.png")


# ---------------------------------------------- F. world map (optional) -----
try:
    import plotly.express as px
except ImportError:
    print("plotly not installed - skipping map (pip install plotly)")
else:
    latest = pct.columns.max()
    m = (countries[(countries["Indicator Code"] == IND["pct1990"])
                   & (countries["Year"] == latest)].copy())
    labels = ["Fell > 50%", "Fell 0–50%", "Rose 0–100%", "Rose 100–500%",
              "Rose 500–1,000%", "Rose > 1,000%"]
    m["band"] = pd.cut(m["Value"], [-100, -50, 0, 100, 500, 1000, np.inf],
                       labels=labels)
    fig = px.choropleth(
        m, locations="Country Code", color="band",
        category_orders={"band": labels},
        color_discrete_sequence=["#1757ac", "#84b9f3", "#f8b4a0",
                                 "#f2876b", "#e4573e", "#8f1d14"],
        hover_name="Country Name", hover_data={"Value": ":,.0f", "band": False,
                                               "Country Code": False},
        title=f"CO₂ emissions: % change from 1990 to {latest}")
    fig.update_layout(legend_title_text="", geo=dict(showframe=False))
    fig.write_html(OUT / "F_world_map.html")
    print("saved", OUT / "F_world_map.html")

print("done")
