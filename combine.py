#!/usr/bin/env python3
"""Combine historical observations and forecast data into per-city JSON files."""

import json
import math
from datetime import datetime
from pathlib import Path

import pandas as pd
import pytz

# Configuration
CITIES = ["Melbourne", "Sydney"]
VARIABLES = ["temperature_2m", "cloud_cover", "precipitation", "relative_humidity_2m"]
# Variables only available in forecast data (not in archive)
FORECAST_ONLY_VARS = ["precipitation_probability"]
# Variables that should only show today's data (no historic ghost lines)
TODAY_ONLY_VARS = ["cloud_cover"]
# Variables whose bands are precomputed and historic data stripped from output
BAND_VARS = ["temperature_2m", "relative_humidity_2m"]
# Variables to strip historic entries from (keep only today + future)
TODAY_FUTURE_VARS = ["temperature_2m", "relative_humidity_2m", "precipitation"]

BASE_DIR = Path(__file__).parent
ARCHIVE_DIR = BASE_DIR / "new_data" / "observations" / "archive"
FORECAST_DIR = BASE_DIR / "new_data" / "forecasts"
GEOCODE_CACHE = BASE_DIR / "new_data" / "geocode_cache.json"
OUTPUT_DIR = BASE_DIR / "dash" / "static" / "cities"


def load_city_timezones():
    with open(GEOCODE_CACHE) as f:
        cache = json.load(f)
    return {city: data["timezone"] for city, data in cache.items()}


def load_observations(city, tz, today):
    """Load all parquet files for the current month, filter to city.

    Returns all days in the month across all years (not just today's day),
    giving a richer set of ghost lines.
    """
    month = today.month
    pattern = f"*-{month:02d}.parquet"
    files = sorted(ARCHIVE_DIR.glob(pattern))

    if not files:
        return pd.DataFrame()

    dfs = []
    for f in files:
        df = pd.read_parquet(f)
        df = df[df["city"] == city]
        if df.empty:
            continue
        dfs.append(df)

    if not dfs:
        return pd.DataFrame()

    df = pd.concat(dfs, ignore_index=True)
    df["time"] = pd.to_datetime(df["time"], utc=True)
    return df


def load_forecast(city):
    """Load forecast JSON for a city."""
    forecast_file = FORECAST_DIR / f"{city}.json"
    if not forecast_file.exists():
        return pd.DataFrame()

    with open(forecast_file) as f:
        data = json.load(f)

    records = data.get("hourly", [])
    if not records:
        return pd.DataFrame()

    df = pd.DataFrame(records)
    df["time"] = pd.to_datetime(df["time"], utc=True)
    return df


def combine_city(city, tz_name):
    tz = pytz.timezone(tz_name)
    today = datetime.now(tz)

    obs = load_observations(city, tz, today)
    forecast = load_forecast(city)

    if obs.empty and forecast.empty:
        print(f"  No data for {city}")
        return

    # Tag source for dedup priority (obs wins)
    if not obs.empty:
        obs = obs.copy()
        obs["_source"] = "obs"
    if not forecast.empty:
        forecast = forecast.copy()
        forecast["_source"] = "forecast"

    # Concat and deduplicate, keeping observations over forecasts
    parts = [df for df in [obs, forecast] if not df.empty]
    combined = pd.concat(parts, ignore_index=True)
    combined = combined.sort_values(["time", "_source"])  # obs < forecast alphabetically
    combined = combined.drop_duplicates(subset=["time"], keep="first")  # keep obs
    combined = combined.sort_values("time").reset_index(drop=True)

    # Convert to local timezone and format
    combined["time"] = combined["time"].dt.tz_convert(tz)

    # Filter today-only data (for cloud_cover etc.)
    today_str = today.strftime("%Y-%m-%d")
    today_only = combined[combined["time"].dt.strftime("%Y-%m-%d") == today_str]

    # Build output
    all_vars = VARIABLES + FORECAST_ONLY_VARS
    output = {}
    for var in all_vars:
        if var not in combined.columns:
            continue
        # Use today-only data for certain variables
        source = today_only if var in TODAY_ONLY_VARS else combined
        records = []
        for _, row in source.iterrows():
            val = row[var]
            if pd.isna(val):
                continue
            records.append({
                "time": row["time"].isoformat(),
                "value": round(float(val), 1),
            })
        output[var] = records

    # Compute hourly averages from historic observations only (exclude forecast)
    if not obs.empty:
        obs_local = obs.copy()
        obs_local["time"] = pd.to_datetime(obs_local["time"], utc=True).dt.tz_convert(tz)
        obs_local["hour"] = obs_local["time"].dt.hour

        for var in BAND_VARS:
            if var not in obs_local.columns:
                continue
            avg = obs_local.groupby("hour")[var].mean()
            output[f"{var}_avg"] = [
                {"hour": int(h), "value": round(float(v), 1)}
                for h, v in avg.sort_index().items()
                if not pd.isna(v)
            ]

        # Compute quantile bands for BAND_VARS
        for var in BAND_VARS:
            if var not in obs_local.columns:
                continue
            avg_by_hour = obs_local.groupby("hour")[var].mean()

            def _quantile(arr, q):
                """Linear interpolation quantile matching the JS implementation."""
                if len(arr) == 0:
                    return float("nan")
                pos = q * (len(arr) - 1)
                lo = int(math.floor(pos))
                hi = int(math.ceil(pos))
                if lo == hi:
                    return arr[lo]
                return arr[lo] + (arr[hi] - arr[lo]) * (pos - lo)

            boundaries = {}
            for h in range(24):
                avg_val = avg_by_hour.get(h)
                if avg_val is None or pd.isna(avg_val):
                    continue
                vals = obs_local.loc[obs_local["hour"] == h, var].dropna().sort_values().tolist()
                if not vals:
                    continue
                below = sorted([v for v in vals if v <= avg_val])
                above = sorted([v for v in vals if v > avg_val])
                boundaries[h] = [
                    _quantile(below, 0),
                    _quantile(below, 1 / 3),
                    _quantile(below, 2 / 3),
                    float(avg_val),
                    _quantile(above, 1 / 3) if above else float(avg_val),
                    _quantile(above, 2 / 3) if above else float(avg_val),
                    _quantile(above, 1) if above else float(avg_val),
                ]

            bands = []
            for b in range(6):
                data = []
                for h in range(24):
                    if h not in boundaries:
                        continue
                    data.append({
                        "hour": h,
                        "lower": round(boundaries[h][b], 1),
                        "upper": round(boundaries[h][b + 1], 1),
                    })
                bands.append(data)
            output[f"{var}_bands"] = bands

    # Strip historic entries — keep only today + future
    for var in TODAY_FUTURE_VARS:
        if var not in output:
            continue
        output[var] = [
            entry for entry in output[var]
            if entry["time"][:10] >= today_str
        ]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"{city}.json"
    with open(out_path, "w") as f:
        json.dump(output, f)

    counts = {v: len(output.get(v, [])) for v in all_vars if v in output}
    print(f"  {city}: {counts} written to {out_path}")


def main():
    city_timezones = load_city_timezones()

    built_cities = []
    for city in CITIES:
        tz_name = city_timezones.get(city)
        if not tz_name:
            print(f"  Skipping {city}: no timezone in geocode cache")
            continue
        combine_city(city, tz_name)
        built_cities.append(city)

    # Write city list for the frontend
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    list_path = OUTPUT_DIR / "_list.json"
    with open(list_path, "w") as f:
        json.dump(built_cities, f)
    print(f"  City list: {built_cities} written to {list_path}")


if __name__ == "__main__":
    main()
