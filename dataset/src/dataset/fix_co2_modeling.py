"""
Fix the WDI CO2 modeling dataset and compute a naive baseline.

What it fixes (numbers refer to the review):
  1. Leaky growth rate     -> recomputed from PAST years only (t-2 -> t-1)
  2. Empty-target rows     -> dropped
  3. Mixed indicators      -> one file per indicator (+ a combined long file)
  4. Regional aggregates   -> removed, countries only
  6. Redundant / leaky cols -> Value, Value Original, Sufficient History,
                               Series Observation Count dropped;
                               a train-only observation count is added instead
  7. Exploding growth on "% change from 1990" -> clipped to +/-GROWTH_CLIP
Also adds:
  - Target Change: y(t) - y(t-1), a better target than the raw level
  - Baseline report: "same as last year" scores to beat, per indicator and split

All lag / rolling / growth features are rebuilt on a complete year grid per
country+indicator, so "Lag 1" always means exactly one calendar year earlier.

Usage:
    python fix_co2_modeling.py wdi_co2_modeling_ready.csv [output_dir]
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

# ----------------------------------------------------------------- config ---
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("wdi_co2_modeling_ready.csv")
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("co2_model_fixed")
OUT.mkdir(parents=True, exist_ok=True)

# Same time-based split as the original file
SPLITS = [("train", 1960, 2015), ("validation", 2016, 2019), ("test", 2020, 2025)]

GROWTH_CLIP = 5.0  # growth rates are fractions: 5.0 = +500%

KEYS = ["Country Name", "Country Code", "Indicator Name", "Indicator Code"]
GROUP = ["Country Code", "Indicator Code"]

AGGREGATES = {
    "AFE", "AFW", "ARB", "CEB", "CSS", "EAP", "EAR", "EAS", "ECA", "ECS", "EMU",
    "EUU", "FCS", "HIC", "HPC", "IBD", "IBT", "IDA", "IDB", "IDX", "LAC", "LCN",
    "LDC", "LIC", "LMC", "LMY", "LTE", "MEA", "MIC", "MNA", "NAC", "OED", "OSS",
    "PRE", "PSS", "PST", "SAS", "SSA", "SSF", "SST", "TEA", "TEC", "TLA", "TMN",
    "TSA", "TSS", "UMC", "WLD",
}

SHORT = {"EN.GHG.CO2.ZG.AR5": "pct_change_1990",
         "NY.ADJ.DCO2.CD": "damage_usd",
         "NY.ADJ.DCO2.GN.ZS": "damage_gni"}


def assign_split(year):
    for name, lo, hi in SPLITS:
        if lo <= year <= hi:
            return name
    return None


# ------------------------------------------------------------------- load ---
raw = pd.read_csv(SRC)
print(f"Loaded {len(raw):,} rows")

# 4. countries only
df = raw[~raw["Country Code"].isin(AGGREGATES)].copy()
print(f"Removed {len(raw) - len(df):,} aggregate rows "
      f"({raw['Country Code'].isin(AGGREGATES).groupby(raw['Country Code']).any().sum()} aggregates)")

# 6. keep only what we need; Value Model is the target, the flag stays
df = df[KEYS + ["Year", "Value Model", "Was Interpolated"]]
df = df.rename(columns={"Value Model": "Target"})


# ------------------------------------------- rebuild features, no leakage ---
def build_features(g):
    """g: one country+indicator series. Reindex to every year, then
    build features that only look at years BEFORE the current one."""
    g = g.set_index("Year").sort_index()
    years = range(g.index.min(), g.index.max() + 1)
    g = g.reindex(years)
    g[KEYS] = g[KEYS].ffill().bfill()
    g["Was Interpolated"] = g["Was Interpolated"].fillna(False).astype(bool)

    y = g["Target"]
    past = y.shift(1)                          # everything below uses past only
    g["Lag 1"] = past
    g["Lag 3"] = y.shift(3)
    g["Lag 5"] = y.shift(5)
    g["Rolling Mean 3"] = past.rolling(3).mean()
    g["Rolling Mean 5"] = past.rolling(5).mean()
    g["Rolling Std 3"] = past.rolling(3).std()
    # 1. growth from t-2 to t-1 (NOT t-1 to t, which leaked the target)
    g["Growth Rate Lag 1"] = past.pct_change(fill_method=None)
    # Better target: the change this year (model predicts movement, not level)
    g["Target Change"] = y - past
    return g.reset_index().rename(columns={"index": "Year"})


# Loop instead of groupby.apply so it behaves the same on pandas 1.x, 2.x and 3.x
df = pd.concat([build_features(g) for _, g in df.groupby(GROUP)],
               ignore_index=True)

# 7. growth rates explode when the base is near zero (esp. "% change from 1990")
g = df["Growth Rate Lag 1"].replace([np.inf, -np.inf], np.nan)
df["Growth Rate Lag 1"] = g.clip(-GROWTH_CLIP, GROWTH_CLIP)

# 2. drop rows with no target (padding years, gaps)
before = len(df)
df = df.dropna(subset=["Target"])
print(f"Dropped {before - len(df):,} rows with no target")

df["Split"] = df["Year"].map(assign_split)
df = df.dropna(subset=["Split"])

# 6b. replacement for Series Observation Count: count TRAIN years only,
#     so the feature never sees validation/test years
train_counts = (df[df["Split"] == "train"].groupby(GROUP).size()
                .rename("Train Obs Count"))
df = df.merge(train_counts, on=GROUP, how="left")
df["Train Obs Count"] = df["Train Obs Count"].fillna(0).astype(int)


# ------------------------------------------------------------ leakage check -
FEATURES = ["Lag 1", "Lag 3", "Lag 5", "Rolling Mean 3", "Rolling Mean 5",
            "Rolling Std 3", "Growth Rate Lag 1", "Train Obs Count"]
m = df.dropna(subset=["Lag 1", "Growth Rate Lag 1"])
rebuilt = m["Lag 1"] * (1 + m["Growth Rate Lag 1"])
leak_share = np.isclose(rebuilt, m["Target"], rtol=1e-6).mean()
print(f"Leakage check - target rebuilt from Lag1*(1+Growth): {leak_share:.1%} "
      f"(was 100% before the fix)")
assert leak_share < 0.05, "growth feature still reconstructs the target"


# ------------------------------------------------------------- save files ---
cols = (KEYS + ["Year", "Split", "Target", "Target Change", "Was Interpolated"]
        + FEATURES)
df = df[cols].sort_values(GROUP + ["Year"])

df.to_csv(OUT / "co2_model_fixed_long.csv", index=False)
print("saved", OUT / "co2_model_fixed_long.csv", f"({len(df):,} rows)")

# 3. one file per indicator - train a separate model on each
for code, sub in df.groupby("Indicator Code"):
    path = OUT / f"co2_model_{SHORT.get(code, code)}.csv"
    sub.to_csv(path, index=False)
    print("saved", path, f"({len(sub):,} rows)")


# ---------------------------------------------------------- baseline report -
def scores(y, p):
    err = y - p
    ss_tot = ((y - y.mean()) ** 2).sum()
    return {"MAE": err.abs().mean(),
            "RMSE": np.sqrt((err ** 2).mean()),
            "R2": 1 - (err ** 2).sum() / ss_tot if ss_tot else np.nan}


rows = []
for (code, split), sub in df.dropna(subset=["Lag 1"]).groupby(["Indicator Code", "Split"]):
    s = scores(sub["Target"], sub["Lag 1"])       # predict: same as last year
    rows.append({"indicator": SHORT.get(code, code), "split": split,
                 "rows": len(sub), "years": f"{sub.Year.min()}–{sub.Year.max()}", **s})
report = pd.DataFrame(rows)
report["split"] = pd.Categorical(report["split"], ["train", "validation", "test"])
report = report.sort_values(["indicator", "split"])
report.to_csv(OUT / "baseline_report.csv", index=False)

pd.set_option("display.width", 140)
print("\nBaseline to beat - predict this year = last year:")
print(report.to_string(index=False, float_format=lambda v: f"{v:,.4g}"))
print("\nIf you model 'Target Change', the same baseline is predicting 0 change "
      "(identical errors). A useful model must beat these numbers.")
