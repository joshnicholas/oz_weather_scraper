# %%
import pandas as pd
import os
import requests
from io import StringIO
import time
import json 

import datetime
import pytz
import pathlib

pathos = pathlib.Path(__file__).parent
os.chdir(pathos)

today = datetime.datetime.now()
scrape_date_stemmo = today.astimezone(pytz.timezone("Australia/Brisbane")).strftime('%Y%m%d')
scrape_hour = today.astimezone(pytz.timezone("Australia/Brisbane")).strftime('%H')
today_for_loop = today.astimezone(pytz.timezone("Australia/Brisbane"))

def if_no_fold_create(pathos, to_check):
    if pathos[-1] != '/':
        pathos += '/'

    folds = os.listdir(pathos)

    if to_check not in folds:
        os.mkdir(f"{pathos}{to_check}")

def rand_delay(num):
  import random
  import time
  rando = random.random() * num
#   print(rando)
  time.sleep(rando)

def convert_to_legacy_format(df):

    # Create new dataframe with mapped columns
    converted = pd.DataFrame()

    # Time formatting: convert from "25/09:30am" to "9:30 am"
    converted['Time (AEDT)'] = df['local_date_time[80]'].str.extract(r'\d+/(\d+:\d+(?:am|pm))', expand=False)
    converted['Time (AEDT)'] = converted['Time (AEDT)'].str.replace('am', ' am').str.replace('pm', ' pm')

    # Temperature columns
    converted['Temp (°C)'] = df['air_temp']
    converted['Feels Like (°C)'] = df['apparent_t']
    converted['Humidity(%)'] = df['rel_hum']

    # Wind columns
    converted['Wind Direction'] = df['wind_dir[80]']
    # Combine wind speed in both units: "7 4" format (kmh, knots)
    converted['Wind Speed (km/h) (knots)'] = df['wind_spd_kmh'].astype(str) + ' ' + df['wind_spd_kt'].astype(str)
    converted['Wind Gust (km/h) (knots)'] = df['gust_kmh'].astype(str) + ' ' + df['gust_kt'].astype(str)
    # Replace -9999 with "–"
    converted['Wind Speed (km/h) (knots)'] = converted['Wind Speed (km/h) (knots)'].str.replace(r'-9999\.0|-9999', '–', regex=True)
    converted['Wind Gust (km/h) (knots)'] = converted['Wind Gust (km/h) (knots)'].str.replace(r'-9999\.0|-9999', '–', regex=True)

    # Pressure
    converted['Pressure (hPa)'] = df['press_qnh']

    # Rainfall
    converted['Rainfall since 9 am (mm)'] = df['rain_trace[80]']

    # Date formatting: convert from "20251025093000" to "2025-10-25"
    converted['Date'] = pd.to_datetime(df['local_date_time_full[80]'], format='%Y%m%d%H%M%S').dt.strftime('%Y-%m-%d')

    return converted

def save_data(df, folder_path, dropcol):
    """
    Save dataframe to monthly parquet file with deduplication.

    Args:
        df: pandas DataFrame to save
        folder_path: path to folder where parquet files are stored
        dropcol: column name to use for deduplication
    """
    # Get current year-month for filename
    current_month = today.astimezone(pytz.timezone("Australia/Brisbane")).strftime('%Y-%m')
    filename = f"{current_month}.parquet"
    filepath = os.path.join(folder_path, filename)

    # Create folder if it doesn't exist
    os.makedirs(folder_path, exist_ok=True)

    # Check if file exists for current month
    if os.path.exists(filepath):
        # Read existing data
        existing_df = pd.read_parquet(filepath)
        # Append new data
        combined_df = pd.concat([existing_df, df], ignore_index=True)
        # Ensure dropcol is string type for consistent sorting and remove any .0 suffix
        combined_df[dropcol] = combined_df[dropcol].astype(str).str.replace(r'\.0$', '', regex=True)
        # Ensure numeric columns are properly typed
        numeric_cols = ['sort_order', 'wmo', 'lat', 'lon', 'air_temp', 'apparent_t',
                        'rel_hum', 'wind_spd_kmh', 'wind_spd_kt', 'gust_kmh',
                        'gust_kt', 'press_qnh', 'rain_trace[80]']
        for col in numeric_cols:
            if col in combined_df.columns:
                combined_df[col] = pd.to_numeric(combined_df[col], errors='coerce')
        # Drop duplicates based on timestamp
        combined_df = combined_df.drop_duplicates(subset=[dropcol], keep='last')
        # Sort by the deduplication column
        combined_df = combined_df.sort_values(by=dropcol)
        # Save back to file
        combined_df.to_parquet(filepath, index=False)

    else:
        # Sort before creating new file
        df = df.sort_values(by=dropcol)
        # Create new file
        df.to_parquet(filepath, index=False)

    # If Melbourne, create last 30 days JSON (only for observation data)
    if "Melbourne" in folder_path and 'local_date_time_full[80]' in df.columns:
        # Read all parquet files in the folder
        parquet_files = sorted([f for f in os.listdir(folder_path) if f.endswith('.parquet')])

        if parquet_files:
            # Read all parquet files and combine
            all_data = []
            for pf in parquet_files:
                pf_path = os.path.join(folder_path, pf)
                all_data.append(pd.read_parquet(pf_path))

            full_df = pd.concat(all_data, ignore_index=True)

            # Check if this is observation data (has required columns)
            required_cols = ['local_date_time_full[80]', 'air_temp', 'rain_trace[80]', 'wind_spd_kmh', 'rel_hum']
            if all(col in full_df.columns for col in required_cols):
                # Convert timestamp to datetime and extract date/hour
                full_df['datetime'] = pd.to_datetime(full_df['local_date_time_full[80]'], format='%Y%m%d%H%M%S')
                full_df['Date'] = full_df['datetime'].dt.strftime('%Y-%m-%d')
                full_df['Hour'] = full_df['datetime'].dt.hour

                # Filter last 30 days (make cutoff timezone-naive to match datetime column)
                cutoff_date = today.replace(tzinfo=None) - datetime.timedelta(days=30)
                full_df = full_df[full_df['datetime'] >= cutoff_date]

                # Select and rename columns
                last30 = full_df[['Date', 'Hour', 'air_temp', 'rain_trace[80]', 'wind_spd_kmh', 'rel_hum']].copy()
                last30.rename(columns={
                    'air_temp': 'Temp',
                    'rain_trace[80]': 'Rain',
                    'wind_spd_kmh': 'Wind',
                    'rel_hum': 'Humidity'
                }, inplace=True)

                # Drop duplicates based on Date + Hour (keep most recent)
                last30 = last30.drop_duplicates(subset=['Date', 'Hour'], keep='last')

                # Sort by Date and Hour
                last30 = last30.sort_values(['Date', 'Hour'])

                # Save to melbs/static/last30.json
                os.makedirs('melbs/static', exist_ok=True)
                last30.to_json('melbs/static/last30.json', orient='records', indent=2)

def dumper(path, name, frame):
    with open(f'{path}/{name}.csv', 'w') as f:
        frame.to_csv(f, index=False, header=True)

def convert_observations_to_melbs_format(df):
    """
    Convert observations dataframe to Melbourne static format.
    Expected format: {"Date": "YYYY-MM-DD", "Temp": float, "Rain": float, "Wind": float, "Humidity": float}

    Args:
        df: DataFrame with legacy format columns (Time (AEDT), Temp (°C), etc.)

    Returns:
        DataFrame ready for melbs/static/observations.json
    """
    # Parse hour from Time column
    df = df.copy()
    df['Hour'] = df['Time (AEDT)'].str.extract(r'(\d+):\d+').astype(float)
    df['is_pm'] = df['Time (AEDT)'].str.contains('pm')
    # Convert to 24-hour format
    df['Hour24'] = df.apply(lambda row: row['Hour'] if not row['is_pm'] or row['Hour'] == 12
                            else row['Hour'] + 12 if row['Hour'] != 12
                            else 12 if row['is_pm']
                            else row['Hour'], axis=1)

    results = []

    for date, group in df.groupby('Date'):
        # Max temp (unchanged)
        max_temp = group['Temp (°C)'].max()

        # Calculate rainfall since midnight
        # Rain accumulates from 9am and resets at 9am
        # To get rain since midnight, we need:
        # 1. Rain from midnight to 9am (last value before 9am)
        # 2. Rain from 9am onwards (last value of the day)

        before_9am = group[group['Hour24'] < 9]
        after_9am = group[group['Hour24'] >= 9]

        rain_midnight_to_9am = before_9am['Rainfall since 9 am (mm)'].iloc[-1] if len(before_9am) > 0 else 0
        rain_9am_onwards = after_9am['Rainfall since 9 am (mm)'].iloc[-1] if len(after_9am) > 0 else 0

        total_rain = rain_midnight_to_9am + rain_9am_onwards

        # Wind and humidity (unchanged for now)
        max_wind = group['Wind Speed (km/h) (knots)'].str.extract(r'(\d+)').astype(float).max()[0] if group['Wind Speed (km/h) (knots)'].notna().any() else None
        avg_humidity = group['Humidity(%)'].mean()

        results.append({
            'Date': date,
            'Temp': max_temp,
            'Rain': total_rain,
            'Wind': max_wind,
            'Humidity': avg_humidity
        })

    daily_summary = pd.DataFrame(results)

    # Drop rows with all null values for the weather data
    daily_summary = daily_summary.dropna(subset=['Temp', 'Rain', 'Wind', 'Humidity'], how='all')

    return daily_summary



def grab_observations(csv_pathos, stem):
    r = requests.get(csv_pathos)
    tab = pd.read_csv(StringIO(r.text), skiprows=19)

    if_no_fold_create('data/new', stem)

    save_data(tab, f'data/new/{stem}', 'local_date_time_full[80]')

    # tab = tab[[ 'local_date_time_full[80]','local_date_time[80]','apparent_t','rel_hum', ]]

    outty = convert_to_legacy_format(tab)
    outty.dropna(subset=['Time (AEDT)'], inplace=True)

    print(outty)
    # print(outty.columns.tolist())

    dumper(f"data", stem, outty)


    if stem == "Melbourne":
        melbs_observations = convert_observations_to_melbs_format(outty)
        melbs_observations.to_json('melbs/static/observations.json', orient='records', indent=2)


    rand_delay(2)


grab_observations("https://reg.bom.gov.au/fwo/IDV60901/IDV60901.95936.axf", 'Melbourne')
