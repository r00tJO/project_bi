from pathlib import Path
import json
import re
import numpy as np
import pandas as pd

INPUT = Path("./input/WDICSV.csv")
OUT_DIR = Path("./output")
ID_COLS = ['Country Name', 'Country Code', 'Indicator Name', 'Indicator Code']


def load_wdi(path, usecols=None):
    """
        Load a WDI CSV and remove whitespace from column labels.
    """
    df = pd.read_csv(path, usecols=usecols, low_memory=False, encoding='utf-8-sig')
    df.columns = df.columns.str.strip()
    return df


def find_year_columns(df, min_year=1960, max_year=2100):
    """
        Return columns whose names are four-digit years in the accepted range.
    """
    return [c for c in df.columns if str(c).isdigit() and min_year <= int(c) <= max_year]


def select_co2_indicators(df):
    """
        Select direct CO2/carbon-dioxide indicators, excluding unrelated CO2e/GHG rows.
    """
    name = df['Indicator Name'].fillna('').str.lower()
    direct = name.str.contains(r'\bco2\b|carbon dioxide', regex=True)
    exclude = name.str.contains(r'co2 equivalent|co2e|greenhouse gas|ghg', regex=True)
    return df.loc[direct & ~exclude].copy()


def remove_exact_duplicates(df):
    """
        Remove exact duplicate source rows.
    """
    return df.drop_duplicates().copy()


def reshape_to_long(df):
    """
        Reshape WDI year columns into tidy country-indicator-year observations.
    """
    year_cols = find_year_columns(df)
    long_df = df.melt(
        id_vars=ID_COLS,
        value_vars=year_cols,
        var_name='Year',
        value_name='Value'
    )
    long_df['Year'] = pd.to_numeric(long_df['Year'], errors='coerce').astype('Int16')
    long_df['Value'] = pd.to_numeric(long_df['Value'], errors='coerce')
    return long_df


def clean_long_data(df, drop_missing_values=True):
    """
        Standardize identifiers, remove invalid keys, and optionally remove missing values.
    """
    out = df.copy()
    for col in ID_COLS:
        out[col] = out[col].astype('string').str.strip()
    out = out.dropna(subset=['Country Name', 'Country Code', 'Indicator Name',
                             'Indicator Code', 'Year'])
    if drop_missing_values:
        out = out.dropna(subset=['Value'])
    out = out.drop_duplicates(subset=['Country Code', 'Indicator Code', 'Year'], keep='last')
    return out.sort_values(['Country Code', 'Indicator Code', 'Year']).reset_index(drop=True)


def add_series_quality_flags(df, min_observations=10):
    """
        Add observation coverage flags without changing or imputing original values.
    """
    out = df.copy()
    keys = ['Country Code', 'Indicator Code']
    counts = out.groupby(keys)['Value'].transform('count')
    out['Series Observation Count'] = counts.astype('Int32')
    out['Sufficient History'] = counts.ge(min_observations)
    return out


def interpolate_internal_gaps(df, max_gap=3):
    """
        Create a separate modeling value; fill only internal gaps, never extrapolate edges.
    """
    out = df.sort_values(['Country Code', 'Indicator Code', 'Year']).copy()
    keys = ['Country Code', 'Indicator Code']
    out['Value Original'] = out['Value']
    out['Value Model'] = out.groupby(keys, group_keys=False)['Value'].transform(
        lambda s: s.interpolate(method='linear', limit=max_gap, limit_area='inside')
    )
    out['Was Interpolated'] = out['Value'].isna() & out['Value Model'].notna()
    return out


def add_time_series_features(df, value_col='Value Model', lags=(1, 3, 5), windows=(3, 5)):
    """
        Add leakage-safe lagged predictors using only earlier years in each series.
    """
    out = df.sort_values(['Country Code', 'Indicator Code', 'Year']).copy()
    group = out.groupby(['Country Code', 'Indicator Code'])[value_col]
    for lag in lags:
        out[f'{value_col} Lag {lag}'] = group.shift(lag)
    previous = group.shift(1)
    for window in windows:
        out[f'{value_col} Rolling Mean {window}'] = previous.groupby(
            [out['Country Code'], out['Indicator Code']]
        ).transform(lambda s: s.rolling(window, min_periods=window).mean())
    out[f'{value_col} Growth Rate'] = group.pct_change(fill_method=None).replace([np.inf, -np.inf], np.nan)
    return out


def add_chronological_split(df, train_end=2015, validation_end=2019):
    """
        Label chronological partitions to prevent future-to-past leakage.
    """
    out = df.copy()
    out['Split'] = np.select(
        [out['Year'] <= train_end, out['Year'] <= validation_end],
        ['train', 'validation'],
        default='test'
    )
    return out


def create_indicator_catalog(df):
    """
        Summarize indicator coverage for choosing visualization and prediction targets.
    """
    return (df.groupby(['Indicator Code', 'Indicator Name'], as_index=False)
              .agg(Observations=('Value', 'count'),
                   Countries=('Country Code', 'nunique'),
                   First_Year=('Year', 'min'),
                   Last_Year=('Year', 'max'),
                   Missing_Values=('Value', lambda s: int(s.isna().sum())))
              .sort_values(['Observations', 'Indicator Code'], ascending=[False, True]))


def prepare_all(input_path=INPUT, output_dir=OUT_DIR):
    raw = load_wdi(input_path)
    co2_wide = remove_exact_duplicates(select_co2_indicators(raw))
    long_with_missing = clean_long_data(reshape_to_long(co2_wide), drop_missing_values=False)
    viz = add_series_quality_flags(long_with_missing.dropna(subset=['Value']))
    catalog = create_indicator_catalog(long_with_missing)

    model_base = add_series_quality_flags(long_with_missing)
    model = interpolate_internal_gaps(model_base, max_gap=3)
    model = model[model['Sufficient History']].copy()
    model = add_time_series_features(model)
    model = add_chronological_split(model)

    viz_path = output_dir / 'wdi_co2_visualization_ready.csv'
    model_path = output_dir / 'wdi_co2_modeling_ready.csv'
    catalog_path = output_dir / 'wdi_co2_indicator_catalog.csv'
    co2_wide_path = output_dir / 'wdi_co2_wide_filtered.csv'
    co2_wide.to_csv(co2_wide_path, index=False)
    viz.to_csv(viz_path, index=False)
    model.to_csv(model_path, index=False)
    catalog.to_csv(catalog_path, index=False)

    summary = {
        'source_rows': int(len(raw)),
        'co2_source_rows': int(len(co2_wide)),
        'co2_indicators': int(co2_wide['Indicator Code'].nunique()),
        'country_codes_including_aggregates': int(co2_wide['Country Code'].nunique()),
        'visualization_observations': int(len(viz)),
        'modeling_rows_including_missing_targets': int(len(model)),
        'interpolated_values': int(model['Was Interpolated'].sum()),
        'year_min': int(viz['Year'].min()),
        'year_max': int(viz['Year'].max()),
    }
    (output_dir / 'wdi_co2_cleaning_summary.json').write_text(json.dumps(summary, indent=2))
    return summary


if __name__ == '__main__':
    print(json.dumps(prepare_all(), indent=2))
