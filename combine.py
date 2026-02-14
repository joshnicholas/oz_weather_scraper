#!/usr/bin/env python3
"""Combine historical observations and forecast data into per-city JSON files."""

import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import pytz

# Configuration
CITIES = ["Melbourne", "Sydney"]
VARIABLES = ["temperature_2m", "apparent_temperature", "cloud_cover", "precipitation", "relative_humidity_2m"]
# Variables only available in forecast data (not in archive)
FORECAST_ONLY_VARS = ["precipitation_probability"]
# Variables that should only show today's data (no historic ghost lines)
TODAY_ONLY_VARS = ["cloud_cover"]

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
        for var in VARIABLES:
            if var not in obs.columns:
                continue
            obs_local = obs.copy()
            obs_local["time"] = pd.to_datetime(obs_local["time"], utc=True).dt.tz_convert(tz)
            obs_local["hour"] = obs_local["time"].dt.hour
            avg = obs_local.groupby("hour")[var].mean()
            output[f"{var}_avg"] = [
                {"hour": int(h), "value": round(float(v), 1)}
                for h, v in avg.sort_index().items()
                if not pd.isna(v)
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
