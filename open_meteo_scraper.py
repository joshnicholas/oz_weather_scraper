#!/usr/bin/env python3
"""
Open Meteo Weather Scraper

Standalone scraper that collects historical observations and forecasts
for Australian cities using the Open Meteo API. Stores data as JSON
(latest) and monthly Parquet (archive).
"""

import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import openmeteo_requests
import pandas as pd
import requests_cache
from retry_requests import retry

# ─── Configuration ───────────────────────────────────────────────────────────

CITIES = [
    "Melbourne", "Sydney", "Brisbane", "Adelaide",
    "Perth", "Hobart", "Darwin", "Canberra",
]

HISTORY_START_DATE = "2020-01-01"

HOURLY_VARS = [
    "temperature_2m", "apparent_temperature", "dew_point_2m",
    "relative_humidity_2m",
    "precipitation", "rain", "snowfall",
    "cloud_cover",
    "pressure_msl", "surface_pressure",
    "wind_speed_10m", "wind_direction_10m", "wind_gusts_10m",
    "visibility", "uv_index",
    "sunshine_duration",
]

# Additional vars only available in the forecast API (not archive)
FORECAST_EXTRA_HOURLY_VARS = [
    "precipitation_probability",
]

DAILY_VARS = [
    "temperature_2m_max", "temperature_2m_min",
    "precipitation_sum", "rain_sum",
    "wind_speed_10m_max", "wind_gusts_10m_max",
    "uv_index_max",
    "sunrise", "sunset",
]

BASE_DIR = Path(__file__).resolve().parent / "new_data"
GEOCODE_CACHE_PATH = BASE_DIR / "geocode_cache.json"
OBS_DIR = BASE_DIR / "observations"
OBS_ARCHIVE_DIR = OBS_DIR / "archive"
FORECAST_DIR = BASE_DIR / "forecasts"
FORECAST_ARCHIVE_DIR = FORECAST_DIR / "archive"

# Archive API chunk size (days) to stay within API limits
CHUNK_DAYS = 90

# Delay between city requests (seconds) to respect rate limits
REQUEST_DELAY = 1.0

# ─── Setup ───────────────────────────────────────────────────────────────────

def setup_client():
    """Create an Open Meteo API client with caching and retry."""
    cache_session = requests_cache.CachedSession(
        ".openmeteo_cache", expire_after=3600
    )
    retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
    return openmeteo_requests.Client(session=retry_session)


def ensure_dirs():
    """Create all required directories."""
    for d in [OBS_DIR, OBS_ARCHIVE_DIR, FORECAST_DIR, FORECAST_ARCHIVE_DIR]:
        d.mkdir(parents=True, exist_ok=True)


# ─── Geocoding ───────────────────────────────────────────────────────────────

def load_geocode_cache() -> dict:
    if GEOCODE_CACHE_PATH.exists():
        with open(GEOCODE_CACHE_PATH) as f:
            return json.load(f)
    return {}


def save_geocode_cache(cache: dict):
    with open(GEOCODE_CACHE_PATH, "w") as f:
        json.dump(cache, f, indent=2)


def geocode_city(city_name: str) -> dict:
    """Look up a city using the Open Meteo Geocoding API."""
    import requests

    url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {"name": city_name, "count": 1, "language": "en", "format": "json"}
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    if "results" not in data or len(data["results"]) == 0:
        raise ValueError(f"No geocoding results for '{city_name}'")

    result = data["results"][0]
    return {
        "latitude": result["latitude"],
        "longitude": result["longitude"],
        "name": result["name"],
        "country": result.get("country", ""),
        "timezone": result.get("timezone", "UTC"),
    }


def geocode_all_cities(cities: list) -> dict:
    """Geocode all cities, using cache where available."""
    cache = load_geocode_cache()
    updated = False

    for city in cities:
        if city in cache:
            print(f"  Geocode cache hit: {city}")
            continue
        print(f"  Geocoding: {city}...")
        cache[city] = geocode_city(city)
        updated = True
        time.sleep(0.5)

    if updated:
        save_geocode_cache(cache)

    return cache


# ─── Data Fetching ───────────────────────────────────────────────────────────

def api_call_with_rate_limit(client, url, params, max_retries=5):
    """Make an API call with rate-limit retry logic."""
    from openmeteo_requests.Client import OpenMeteoRequestsError

    for attempt in range(max_retries):
        try:
            return client.weather_api(url, params=params)
        except OpenMeteoRequestsError as e:
            if "rate limit" in str(e).lower() or "limit exceeded" in str(e).lower():
                wait = 60 * (attempt + 1)
                print(f"    Rate limited, waiting {wait}s (attempt {attempt + 1}/{max_retries})...")
                time.sleep(wait)
            else:
                raise
    raise RuntimeError(f"Rate limit exceeded after {max_retries} retries")


def fetch_observations(client, lat: float, lon: float,
                       start_date: str, end_date: str) -> pd.DataFrame:
    """Fetch historical observations from the Archive API in chunks."""
    all_frames = []
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")

    while start <= end:
        chunk_end = min(start + timedelta(days=CHUNK_DAYS - 1), end)
        s_str = start.strftime("%Y-%m-%d")
        e_str = chunk_end.strftime("%Y-%m-%d")
        print(f"    Archive: {s_str} → {e_str}")

        responses = api_call_with_rate_limit(
            client,
            "https://archive-api.open-meteo.com/v1/archive",
            params={
                "latitude": lat,
                "longitude": lon,
                "start_date": s_str,
                "end_date": e_str,
                "hourly": HOURLY_VARS,
                "timezone": "UTC",
            },
        )
        response = responses[0]
        hourly = response.Hourly()

        data = {
            "time": pd.date_range(
                start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
                end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
                freq=pd.Timedelta(seconds=hourly.Interval()),
                inclusive="left",
            )
        }
        for i, var in enumerate(HOURLY_VARS):
            data[var] = hourly.Variables(i).ValuesAsNumpy()

        all_frames.append(pd.DataFrame(data))
        start = chunk_end + timedelta(days=1)
        time.sleep(2.0)

    if not all_frames:
        return pd.DataFrame()

    return pd.concat(all_frames, ignore_index=True)


def fetch_forecast(client, lat: float, lon: float) -> tuple:
    """Fetch forecast data. Returns (hourly_df, daily_df)."""
    forecast_hourly_vars = HOURLY_VARS + FORECAST_EXTRA_HOURLY_VARS
    responses = api_call_with_rate_limit(
        client,
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": lat,
            "longitude": lon,
            "hourly": forecast_hourly_vars,
            "daily": DAILY_VARS,
            "timezone": "UTC",
        },
    )
    response = responses[0]

    # Hourly
    hourly = response.Hourly()
    hourly_data = {
        "time": pd.date_range(
            start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
            end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
            freq=pd.Timedelta(seconds=hourly.Interval()),
            inclusive="left",
        )
    }
    for i, var in enumerate(forecast_hourly_vars):
        hourly_data[var] = hourly.Variables(i).ValuesAsNumpy()

    hourly_df = pd.DataFrame(hourly_data)

    # Daily
    daily = response.Daily()
    daily_data = {
        "time": pd.date_range(
            start=pd.to_datetime(daily.Time(), unit="s", utc=True),
            end=pd.to_datetime(daily.TimeEnd(), unit="s", utc=True),
            freq=pd.Timedelta(seconds=daily.Interval()),
            inclusive="left",
        )
    }
    for i, var in enumerate(DAILY_VARS):
        daily_data[var] = daily.Variables(i).ValuesAsNumpy()

    daily_df = pd.DataFrame(daily_data)

    return hourly_df, daily_df


# ─── Storage ─────────────────────────────────────────────────────────────────

def save_json(df: pd.DataFrame, filepath: Path):
    """Save a DataFrame as JSON."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    # Convert timestamps to strings for JSON serialization
    out = df.copy()
    for col in out.select_dtypes(include=["datetime64[ns, UTC]", "datetime64[ns]"]).columns:
        out[col] = out[col].astype(str)
    out.to_json(filepath, orient="records", indent=2)
    print(f"    Saved JSON: {filepath}")


def save_to_parquet(df: pd.DataFrame, archive_dir: Path, dedup_cols: list):
    """Append data to monthly parquet files, deduplicating on dedup_cols."""
    if df.empty:
        return

    archive_dir.mkdir(parents=True, exist_ok=True)

    # Group by year-month
    df = df.copy()
    df["_ym"] = df["time"].dt.tz_localize(None).dt.to_period("M")

    for period, group in df.groupby("_ym"):
        filename = archive_dir / f"{period}.parquet"
        group = group.drop(columns=["_ym"])

        if filename.exists():
            existing = pd.read_parquet(filename)
            combined = pd.concat([existing, group], ignore_index=True)
            combined = combined.drop_duplicates(subset=dedup_cols, keep="last")
            combined = combined.sort_values(dedup_cols).reset_index(drop=True)
            combined.to_parquet(filename, index=False)
            row_count = len(combined)
        else:
            group = group.sort_values(dedup_cols).reset_index(drop=True)
            group.to_parquet(filename, index=False)
            row_count = len(group)

        print(f"    Parquet: {filename} ({row_count} rows)")


def get_last_observation_date(city: str, archive_dir: Path) -> str | None:
    """Find the latest observation date for a city in the archive."""
    parquet_files = sorted(archive_dir.glob("*.parquet"))
    if not parquet_files:
        return None

    # Check the most recent file
    df = pd.read_parquet(parquet_files[-1])
    if "city" in df.columns:
        city_data = df[df["city"] == city]
        if city_data.empty:
            return None
        last_time = city_data["time"].max()
    else:
        last_time = df["time"].max()

    if pd.isna(last_time):
        return None

    return pd.Timestamp(last_time).strftime("%Y-%m-%d")


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("Open Meteo Weather Scraper")
    print("=" * 60)

    ensure_dirs()
    client = setup_client()

    # Geocode
    print("\n[1/3] Geocoding cities...")
    geo = geocode_all_cities(CITIES)

    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")

    # Observations
    print("\n[2/3] Fetching historical observations...")
    for city in CITIES:
        info = geo[city]
        lat, lon = info["latitude"], info["longitude"]
        print(f"\n  {city} ({lat}, {lon})")

        # Determine start date
        last_date = get_last_observation_date(city, OBS_ARCHIVE_DIR)
        if last_date:
            start_date = last_date
            print(f"    Resuming from {start_date}")
        else:
            start_date = HISTORY_START_DATE
            print(f"    Full fetch from {start_date}")

        obs_df = fetch_observations(client, lat, lon, start_date, yesterday)
        if obs_df.empty:
            print(f"    No observation data returned for {city}")
            continue

        obs_df["city"] = city

        # Save latest JSON (last 7 days of available data)
        latest_time = obs_df["time"].max()
        cutoff = latest_time - timedelta(days=7)
        recent_df = obs_df[obs_df["time"] >= cutoff]
        save_json(recent_df, OBS_DIR / f"{city}.json")

        # Save to parquet archive
        save_to_parquet(obs_df, OBS_ARCHIVE_DIR, dedup_cols=["city", "time"])

        time.sleep(REQUEST_DELAY)

    # Forecasts
    print("\n[3/3] Fetching forecasts...")
    for city in CITIES:
        info = geo[city]
        lat, lon = info["latitude"], info["longitude"]
        print(f"\n  {city} ({lat}, {lon})")

        hourly_df, daily_df = fetch_forecast(client, lat, lon)
        hourly_df["city"] = city
        daily_df["city"] = city

        # Save latest JSON (hourly and daily combined into one file)
        forecast_data = {
            "hourly": json.loads(hourly_df.assign(
                time=hourly_df["time"].astype(str)
            ).to_json(orient="records")),
            "daily": json.loads(daily_df.assign(
                time=daily_df["time"].astype(str)
            ).to_json(orient="records")),
        }
        forecast_path = FORECAST_DIR / f"{city}.json"
        with open(forecast_path, "w") as f:
            json.dump(forecast_data, f, indent=2)
        print(f"    Saved JSON: {forecast_path}")

        # Save hourly to parquet archive
        save_to_parquet(hourly_df, FORECAST_ARCHIVE_DIR, dedup_cols=["city", "time"])

        time.sleep(REQUEST_DELAY)

    print("\n" + "=" * 60)
    print("Done!")
    print("=" * 60)


if __name__ == "__main__":
    main()
