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
    # Group by Date and aggregate
    daily_summary = df.groupby('Date').agg({
        'Temp (°C)': 'max',  # Max temp of the day
        'Rainfall since 9 am (mm)': 'last',  # Latest rain observation
        'Wind Speed (km/h) (knots)': lambda x: x.str.extract(r'(\d+)').astype(float).max() if x.notna().any() else None,  # Max wind speed
        'Humidity(%)': 'mean'  # Average humidity
    }).reset_index()

    # Rename columns to match expected format
    daily_summary = daily_summary.rename(columns={
        'Temp (°C)': 'Temp',
        'Rainfall since 9 am (mm)': 'Rain',
        'Wind Speed (km/h) (knots)': 'Wind',
        'Humidity(%)': 'Humidity'
    })

    # Drop rows with all null values for the weather data
    daily_summary = daily_summary.dropna(subset=['Temp', 'Rain', 'Wind', 'Humidity'], how='all')

    return daily_summary

def convert_forecast_to_melbs_format(df):
    """
    Convert forecast dataframe to Melbourne static format.
    Expected format: {"Date": "YYYY-MM-DD", "Max_temp": int, "Rain": int}

    Args:
        df: DataFrame with XML forecast data (date, air_temperature_maximum, precipitation_range, etc.)

    Returns:
        DataFrame ready for melbs/static/forecasts.json
    """
    melbs_forecast = pd.DataFrame()

    melbs_forecast['Date'] = df['date']

    # Extract max temp (remove " Celsius" suffix if present)
    if 'air_temperature_maximum' in df.columns:
        melbs_forecast['Max_temp'] = pd.to_numeric(df['air_temperature_maximum'].str.replace(' Celsius', ''), errors='coerce')

    # Extract rain amount from precipitation_range (e.g., "0 to 3 mm" -> 3)
    if 'precipitation_range' in df.columns:
        # Extract the upper bound of the range
        melbs_forecast['Rain'] = pd.to_numeric(df['precipitation_range'].str.extract(r'to (\d+)')[0], errors='coerce')
    else:
        melbs_forecast['Rain'] = None

    return melbs_forecast

def fetch_forecast(xml_url, city_name):
    """
    Fetch and parse BOM forecast XML feed for a specific city.

    Args:
        xml_url: URL or FTP path to the BOM XML feed
        city_name: City name to match against the 'description' attribute in the XML

    Returns:
        pandas DataFrame with forecast data including dates, temps, precipitation, etc.
    """
    import xml.etree.ElementTree as ET

    # Fetch the XML
    if xml_url.startswith('ftp://'):
        # For FTP URLs, use curl
        import subprocess
        result = subprocess.run(['curl', '-s', xml_url], capture_output=True, text=True)
        xml_content = result.stdout
    else:
        # For HTTP/HTTPS URLs
        r = requests.get(xml_url)
        xml_content = r.text

    # Parse XML
    root = ET.fromstring(xml_content)

    # Find the area matching the city name
    city_area = None
    for area in root.findall('.//area'):
        if area.get('description') == city_name:
            city_area = area
            break

    if city_area is None:
        return pd.DataFrame()

    # Extract forecast periods
    records = []
    for period in city_area.findall('forecast-period'):
        record = {}

        # Get period attributes
        record['index'] = period.get('index')
        record['start_time_local'] = period.get('start-time-local')
        record['end_time_local'] = period.get('end-time-local')
        record['start_time_utc'] = period.get('start-time-utc')
        record['end_time_utc'] = period.get('end-time-utc')

        # Extract date from start time
        if record['start_time_local']:
            record['date'] = pd.to_datetime(record['start_time_local']).strftime('%Y-%m-%d')

        # Extract element data
        for element in period.findall('element'):
            element_type = element.get('type')
            element_units = element.get('units', '')
            value = element.text

            # Store with units if available
            if element_units:
                record[element_type] = f"{value} {element_units}"
            else:
                record[element_type] = value

        # Extract text data (precis, probability of precipitation, etc.)
        for text in period.findall('text'):
            text_type = text.get('type')
            record[text_type] = text.text

        records.append(record)

    # Convert to DataFrame
    df = pd.DataFrame(records)
    df.drop(columns={ 'start_time_local', 'end_time_local', 'start_time_utc', 'end_time_utc',}, inplace=True)

    save_data(df, f'data/forecasts/{city_name}', 'date')

    dumper('data/forecasts', city_name, df)

    # If Melbourne, save to melbs/static/forecasts.json
    if city_name == "Melbourne":
        melbs_forecast = convert_forecast_to_melbs_format(df)
        melbs_forecast.to_json('melbs/static/forecasts.json', orient='records', indent=2)


    # return df

# %%

# https://reg.bom.gov.au/catalogue/data-feeds.shtml

### OBSERVATIONS

# sydney observatory hill:
# https://reg.bom.gov.au/products/IDN60901/IDN60901.94768.shtml
# https://reg.bom.gov.au/fwo/IDN60901/IDN60901.94768.axf

# canberra 
# https://reg.bom.gov.au/products/IDN60903/IDN60903.94926.shtml
# https://reg.bom.gov.au/fwo/IDN60903/IDN60903.94926.axf

# melb
# https://reg.bom.gov.au/products/IDV60901/IDV60901.95936.shtml
# https://reg.bom.gov.au/fwo/IDV60901/IDV60901.95936.axf

## Bris
# https://reg.bom.gov.au/products/IDQ60901/IDQ60901.94576.shtml
# https://reg.bom.gov.au/fwo/IDQ60901/IDQ60901.94576.axf

## Adelaide
# https://reg.bom.gov.au/products/IDS60901/IDS60901.94648.shtml
# https://reg.bom.gov.au/fwo/IDS60901/IDS60901.94648.axf

## Perth
# https://reg.bom.gov.au/products/IDW60901/IDW60901.94608.shtml
# https://reg.bom.gov.au/fwo/IDW60901/IDW60901.94608.axf

## Hobart
# https://reg.bom.gov.au/products/IDT60901/IDT60901.94970.shtml
# https://reg.bom.gov.au/fwo/IDT60901/IDT60901.94970.axf

## Darwin
# https://reg.bom.gov.au/products/IDD60901/IDD60901.94120.shtml

def grab_observations(csv_pathos, stem):
    r = requests.get(csv_pathos)
    tab = pd.read_csv(StringIO(r.text), skiprows=19)

    if_no_fold_create('data/new', stem)

    save_data(tab, f'data/new/{stem}', 'local_date_time_full[80]')

    # tab = tab[[ 'local_date_time_full[80]','local_date_time[80]','apparent_t','rel_hum', ]]

    outty = convert_to_legacy_format(tab)
    outty.dropna(subset=['Time (AEDT)'], inplace=True)

    # print(outty)
    # print(outty.columns.tolist())

    dumper(f"data", stem, outty)


    if stem == "Melbourne":
        melbs_observations = convert_observations_to_melbs_format(outty)
        melbs_observations.to_json('melbs/static/observations.json', orient='records', indent=2)


    rand_delay(2)

    # print(tab)
    # print(tab.columns.tolist())
    # ['sort_order', 'wmo', 'name[80]', 'history_product[80]', 'local_date_time[80]', 
    #  'local_date_time_full[80]', 'aifstime_utc[80]', 'lat', 'lon', 'apparent_t', 'cloud[80]', 
    #  'cloud_base_m', 'cloud_oktas', 'cloud_type_id', 'cloud_type[80]', 'delta_t', 'gust_kmh', 
    #  'gust_kt', 'air_temp', 'dewpt', 'press', 'press_qnh', 'press_msl', 'press_tend[80]', 
    #  'rain_trace[80]', 'rel_hum', 'sea_state[80]', 'swell_dir_worded[80]', 'swell_height', 
    #  'swell_period', 'vis_km[80]', 'weather[80]', 'wind_dir[80]', 'wind_spd_kmh', 'wind_spd_kt']




grab_observations("https://reg.bom.gov.au/fwo/IDN60901/IDN60901.94768.axf", 'Sydney')

grab_observations("https://reg.bom.gov.au/fwo/IDV60901/IDV60901.95936.axf", 'Melbourne')

grab_observations('https://reg.bom.gov.au/fwo/IDQ60901/IDQ60901.94576.axf', 'Brisbane')

grab_observations('https://reg.bom.gov.au/fwo/IDS60901/IDS60901.94648.axf', 'Adelaide')

grab_observations("https://reg.bom.gov.au/fwo/IDW60901/IDW60901.94608.axf", 'Perth')

grab_observations('https://reg.bom.gov.au/fwo/IDT60901/IDT60901.94970.axf', 'Hobart')

grab_observations("https://reg.bom.gov.au/fwo/IDD60901/IDD60901.94120.axf", 'Darwin')




fetch_forecast("ftp://ftp.bom.gov.au/anon/gen/fwo/IDN11060.xml", "Sydney")

fetch_forecast('ftp://ftp.bom.gov.au/anon/gen/fwo/IDV10753.xml', 'Melbourne')

fetch_forecast('ftp://ftp.bom.gov.au/anon/gen/fwo/IDQ11295.xml', 'Brisbane')

fetch_forecast("ftp://ftp.bom.gov.au/anon/gen/fwo/IDN11060.xml", "Canberra")



script_run_time = datetime.datetime.now(pytz.timezone("Australia/Melbourne"))
run_time_data = {
    "lastUpdated": script_run_time.isoformat()
}


run_time_file = "melbs/static/last_updated.json"
with open(run_time_file, 'w') as f:
    json.dump(run_time_data, f, indent=2)