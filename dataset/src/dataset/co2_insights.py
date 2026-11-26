"""
Insight plots for the cleaned World Bank CO2 dataset - one function per plot.

  plot_regions_small_multiples  - how each region's emissions moved vs 1990
  plot_slope_damage_gni         - who got better / worse on CO2 damage (% of GNI)
  plot_heatmap_pct_change       - when growth accelerated or reversed, country x year
  plot_rank_damage_usd          - how the top 10 countries by CO2 damage reshuffled
  plot_scatter_burden_vs_firms  - does a heavier carbon burden go with more firms monitoring CO2?
  plot_world_map                - % change since 1990, banded (optional; needs `pip install plotly`)

Every matplotlib function takes the dict from `load_data()` and returns the
figure, so you can use them one at a time (e.g. in a notebook):

    from co2_insights import load_data, plot_heatmap_pct_change
    data = load_data("Visualization-ready_CO2_dataset.csv")
    fig = plot_heatmap_pct_change(data, top_n=20)

Or run everything from the command line:
    python co2_insights.py path/to/Visualization-ready_CO2_dataset.csv [output_dir]
"""

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.colors import BoundaryNorm, ListedColormap
import numpy as np
import pandas as pd

# ------------------------------------------------------------------ setup ---
IND = {"pct1990": "EN.GHG.CO2.ZG.AR5", "damage_usd": "NY.ADJ.DCO2.CD",
       "damage_gni": "NY.ADJ.DCO2.GN.ZS", "firms": "IC.FRM.CO2.ZS"}

AGGREGATES = {
    "AFE", "AFW", "ARB", "CEB", "CSS", "EAP", "EAR", "EAS", "ECA", "ECS", "EMU",
    "EUU", "FCS", "HIC", "HPC", "IBD", "IBT", "IDA", "IDB", "IDX", "LAC", "LCN",
    "LDC", "LIC", "LMC", "LMY", "LTE", "MEA", "MIC", "MNA", "NAC", "OED", "OSS",
    "PRE", "PSS", "PST", "SAS", "SSA", "SSF", "SST", "TEA", "TEC", "TLA", "TMN",
    "TSA", "TSS", "UMC", "WLD",
}

DAMAGE_END = 2021  # the damage series stop here

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


# ---------------------------------------------------------------- helpers ---
def note(ax, text):
    """Small grey caption under an axes title."""
    ax.text(0, 1.015, text, transform=ax.transAxes, fontsize=9,
            color=C["muted"], va="bottom")


def wide(frame, key):
    """Country x Year table for one indicator."""
    s = frame[frame["Indicator Code"] == IND[key]]
    return s.pivot_table(index="Country Name", columns="Year", values="Value")


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


def load_data(csv_path):
    """Read the CSV, split countries from aggregates, and build the wide tables."""
    df = pd.read_csv(csv_path)
    is_agg = df["Country Code"].isin(AGGREGATES)
    countries, aggregates = df[~is_agg], df[is_agg]
    return {
        "countries": countries,
        "aggregates": aggregates,
        "pct": wide(countries, "pct1990"),
        "usd": wide(countries, "damage_usd"),
        "gni": wide(countries, "damage_gni"),
    }


# ------------------------------------------------------------------ plots ---
def plot_regions_small_multiples(data):
    """A. One panel per region: % change in CO2 emissions since 1990."""
    aggregates = data["aggregates"]
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
    key_ax = axes.flat[-1]
    key_ax.axis("off")
    key_ax.text(0, 0.5, "Blue: the region\nGrey: other regions\nDashed: world",
                fontsize=10, color=C["muted"], va="center", transform=key_ax.transAxes)
    fig.suptitle("CO₂ emissions vs 1990, by region", x=0.06, ha="left",
                 fontsize=14, fontweight="bold")
    fig.text(0.06, 0.925, "Same y-axis in every panel, so heights compare directly",
             fontsize=9.5, color=C["muted"])
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    return fig


def plot_slope_damage_gni(data, start=1995, end=DAMAGE_END, pool=25, n_movers=12):
    """B. Slope chart of CO2 damage (% of GNI) between two years.

    start=1995 because 1990 is missing for many ex-Soviet states.
    Picks the `n_movers` biggest changes among the `pool` largest emitters.
    """
    usd, gni = data["usd"], data["gni"]
    big = usd[end].nlargest(pool).index
    slope = gni.loc[gni.index.isin(big), [start, end]].dropna()
    slope = slope.loc[(slope[end] - slope[start]).abs().nlargest(n_movers).index]

    fig, ax = plt.subplots(figsize=(7.5, 8))
    gap = (slope.values.max() - slope.values.min()) * 0.03
    left_y, right_y = spread(slope[start].values, gap), spread(slope[end].values, gap)
    for (name, (a, b)), ly, ry in zip(slope.iterrows(), left_y, right_y):
        col = C["red"] if b > a else C["blue"]
        ax.plot([0, 1], [a, b], color=col, lw=2, marker="o", ms=6)
        ax.text(-0.04, ly, f"{name} {a:.1f}%", ha="right", va="center", fontsize=8.5)
        ax.text(1.04, ry, f"{b:.1f}% {name}", ha="left", va="center", fontsize=8.5)
    ax.set_xticks([0, 1], [str(start), str(end)])
    ax.set_xlim(-0.9, 1.9)
    ax.yaxis.set_visible(False)
    ax.grid(False)
    ax.spines[["left", "bottom"]].set_visible(False)
    ax.set_title(f"CO₂ damage as % of GNI, {start} → {end}")
    note(ax, f"{n_movers} biggest movers among the {pool} largest emitters · "
             "red = heavier burden, blue = lighter")
    return fig


def plot_heatmap_pct_change(data, top_n=30):
    """C. Country x year heatmap of % change since 1990, banded colours."""
    pct, usd = data["pct"], data["usd"]
    top = usd[DAMAGE_END].nlargest(top_n).index   # biggest emitters by damage
    hm = pct.loc[pct.index.isin(top)]
    hm = hm.loc[hm[hm.columns.max()].sort_values(ascending=False).index]

    bounds = [-100, -50, -25, 0, 50, 100, 200, 400, 1000, 1e6]
    colors = ["#1757ac", "#519ced", "#b6d5f8",                 # falls: blues
              "#fde0d6", "#f8b4a0", "#f2876b", "#e4573e", "#c23324", "#8f1d14"]
    cmap, norm = ListedColormap(colors), BoundaryNorm(bounds, len(colors))

    fig, ax = plt.subplots(figsize=(13, max(4, top_n * 0.3)))
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
    ax.set_title(f"CO₂ emissions vs 1990 — {top_n} largest emitters")
    note(ax, "Sorted by latest value · banded colours keep extreme growers "
             "from washing out the rest")
    return fig


def plot_rank_damage_usd(data, start=1990, end=DAMAGE_END, top_n=10, max_rank=15):
    """D. Bump chart: rank by CO2 damage (US$) over time."""
    usd = data["usd"]
    years = list(range(start, end + 1))
    ranks = usd[years].rank(ascending=False)
    top = ranks[end].nsmallest(top_n).index
    # Also keep anyone who was top 5 at the start but fell out, to show the reshuffle
    dropped = ranks[start].nsmallest(5).index.difference(top)
    show = list(top) + list(dropped)

    fig, ax = plt.subplots(figsize=(11, 6.5))
    for i, name in enumerate(show):
        r = ranks.loc[name, years]
        col = CAT[i] if i < len(CAT) else (C["muted"] if name in top else C["faint"])
        ax.plot(years, r, color=col, lw=2.2, marker="o", ms=3, clip_on=True)
        ax.text(years[-1] + 0.4, r.iloc[-1], name, va="center", fontsize=9)
        if r.iloc[0] <= max_rank:  # only label starting ranks that are on the chart
            ax.text(years[0] - 0.4, r.iloc[0], name, va="center", ha="right",
                    fontsize=8, color=C["muted"])
    ax.set_ylim(max_rank + 0.5, 0.5)  # inverted: rank 1 at the top
    ax.set_yticks(range(1, max_rank + 1))
    ax.set_xlim(start - 5, end + 5)
    ax.set_ylabel("Rank by CO₂ damage (US$)")
    ax.set_title(f"Who causes the most CO₂ damage? Ranking, {start}–{end}")
    note(ax, f"Top {top_n} in {end} (beyond the 8th in grey, faint = was top 5 in "
             f"{start} but fell out) · lines leaving the bottom were ranked below {max_rank}")
    return fig


def plot_scatter_burden_vs_firms(data, year=DAMAGE_END, n_labels=4):
    """E. Scatter: CO2 damage (% of GNI) vs share of firms monitoring CO2."""
    countries, gni = data["countries"], data["gni"]
    firms = (countries[countries["Indicator Code"] == IND["firms"]]
             .sort_values("Year").groupby("Country Name").tail(1)
             .set_index("Country Name")["Value"])
    sc = pd.DataFrame({"burden": gni[year], "firms": firms}).dropna()

    fig, ax = plt.subplots(figsize=(9, 6.5))
    ax.scatter(sc["burden"], sc["firms"], s=40, color=C["blue"], alpha=0.75,
               edgecolor="white", linewidth=1)
    ax.set_xscale("log")
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:g}%"))
    ax.xaxis.set_minor_formatter(mticker.FuncFormatter(
        lambda v, _: f"{v:g}%" if f"{v:g}".lstrip("0.")[:1] in ("2", "5") else ""))
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(decimals=0))
    # Trend on log(x), plus correlation, so the reader sees how weak/strong it is
    x, y = np.log10(sc["burden"]), sc["firms"]
    m, b = np.polyfit(x, y, 1)
    xs = np.linspace(x.min(), x.max(), 50)
    ax.plot(10 ** xs, m * xs + b, color=C["orange"], lw=2)
    r = np.corrcoef(x, y)[0, 1]
    to_label = pd.concat([sc["firms"].nlargest(n_labels),
                          sc["burden"].nlargest(n_labels)]).index.unique()
    for name in to_label:
        ax.annotate(name, (sc.loc[name, "burden"], sc.loc[name, "firms"]),
                    xytext=(5, 3), textcoords="offset points", fontsize=8,
                    color=C["muted"])
    ax.set_xlabel(f"CO₂ damage, % of GNI ({year}, log scale)")
    ax.set_ylabel("Firms monitoring own CO₂ (latest survey)")
    ax.set_title("Heavier carbon burden vs firms tracking emissions")
    note(ax, f"{len(sc)} countries · r = {r:.2f} · exploratory: survey years "
             f"(2021–25) differ from {year}")
    return fig


def plot_world_map(data):
    """F. Interactive choropleth of % change since 1990 (plotly figure).

    Returns None if plotly is not installed.
    """
    try:
        import plotly.express as px
    except ImportError:
        print("plotly not installed - skipping map (pip install plotly)")
        return None
    countries, pct = data["countries"], data["pct"]
    latest = pct.columns.max()
    m = countries[(countries["Indicator Code"] == IND["pct1990"])
                  & (countries["Year"] == latest)].copy()
    labels = ["Fell > 50%", "Fell 0–50%", "Rose 0–100%", "Rose 100–500%",
              "Rose 500–1,000%", "Rose > 1,000%"]
    m["band"] = pd.cut(m["Value"], [-100, -50, 0, 100, 500, 1000, np.inf],
                       labels=labels)
    fig = px.choropleth(
        m, locations="Country Code", color="band",
        category_orders={"band": labels},
        color_discrete_sequence=["#1757ac", "#84b9f3", "#f8b4a0",
                                 "#f2876b", "#e4573e", "#8f1d14"],
        hover_name="Country Name",
        hover_data={"Value": ":,.0f", "band": False, "Country Code": False},
        title=f"CO₂ emissions: % change from 1990 to {latest}")
    fig.update_layout(legend_title_text="", geo=dict(showframe=False))
    return fig


# ------------------------------------------------------------------- main ---
def main(csv_path, out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    data = load_data(csv_path)

    plots = {
        "A_regions_small_multiples.png": plot_regions_small_multiples,
        "B_slope_damage_gni.png": plot_slope_damage_gni,
        "C_heatmap_pct_change.png": plot_heatmap_pct_change,
        "D_rank_damage_usd.png": plot_rank_damage_usd,
        "E_scatter_burden_vs_firms.png": plot_scatter_burden_vs_firms,
    }
    for filename, plot_fn in plots.items():
        fig = plot_fn(data)
        fig.savefig(out_dir / filename)
        plt.close(fig)
        print("saved", out_dir / filename)

    map_fig = plot_world_map(data)
    if map_fig is not None:
        map_fig.write_html(out_dir / "F_world_map.html")
        print("saved", out_dir / "F_world_map.html")
    print("done")


if __name__ == "__main__":
    csv = sys.argv[1] if len(sys.argv) > 1 else "Visualization-ready_CO2_dataset.csv"
    out = sys.argv[2] if len(sys.argv) > 2 else "co2_insights"
    main(csv, out)
