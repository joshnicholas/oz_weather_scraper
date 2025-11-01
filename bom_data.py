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
scrape_time = datetime.datetime.now(pytz.timezone('Australia/Melbourne'))
format_scrape_time = scrape_time.strftime('%Y-%m-%d %H:%M')

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
                # Convert to numeric, then int, then string to handle .0 suffix and NaN values
                full_df['local_date_time_full[80]'] = pd.to_numeric(full_df['local_date_time_full[80]'], errors='coerce')
                full_df = full_df.dropna(subset=['local_date_time_full[80]'])
                full_df['local_date_time_full[80]'] = full_df['local_date_time_full[80]'].astype(int).astype(str)
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
    # Parse hour from Time column to calculate rainfall since midnight
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
        # Sort by hour to ensure chronological order
        group = group.sort_values('Hour24')

        # Max temp (unchanged)
        max_temp = group['Temp (°C)'].max()

        # Calculate rainfall since midnight
        # BOM "Rainfall since 9am" resets at 9am daily
        # Before 9am: shows rain from previous day's 9am (includes midnight to <9am)
        # After 9am: shows rain from current day's 9am onwards
        # Total rain for calendar day = rain_before_9am + rain_after_9am

        before_9am = group[group['Hour24'] < 9]
        after_9am = group[group['Hour24'] >= 9]

        rain_midnight_to_9am = before_9am['Rainfall since 9 am (mm)'].iloc[-1] if len(before_9am) > 0 else 0
        rain_9am_onwards = after_9am['Rainfall since 9 am (mm)'].iloc[-1] if len(after_9am) > 0 else 0

        total_rain = rain_midnight_to_9am + rain_9am_onwards

        # Wind and humidity (unchanged)
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

def convert_forecast_to_melbs_format(df):
    """
    Convert forecast dataframe to Melbourne static format.
    Expected format: {"Date": "YYYY-MM-DD", "Max_temp": int, "Rain_low": int, "Rain_high": int}

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

    # Extract rain amount from precipitation_range (e.g., "0 to 3 mm" -> low=0, high=3)
    if 'precipitation_range' in df.columns:
        # Extract both lower and upper bounds
        melbs_forecast['Rain_low'] = pd.to_numeric(df['precipitation_range'].str.extract(r'(\d+)\s+to')[0], errors='coerce')
        melbs_forecast['Rain_high'] = pd.to_numeric(df['precipitation_range'].str.extract(r'to\s+(\d+)')[0], errors='coerce')
    else:
        melbs_forecast['Rain_low'] = None
        melbs_forecast['Rain_high'] = None

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

def fetch_hourly_forecast_api():
    """
    Fetch hourly forecast data from BOM API endpoints and process it.
    Combines 1-hourly and 3-hourly data into a single dataset.
    """

    # BOM weather icon code to text mapping
    icon_descriptions = {
        1: 'Sunny',
        2: 'Mostly sunny',
        3: 'Partly cloudy',
        4: 'Cloudy',
        6: 'Hazy',
        8: 'Light rain',
        9: 'Wind',
        10: 'Fog',
        11: 'Shower',
        12: 'Rain',
        13: 'Dusty',
        14: 'Frost',
        15: 'Snow',
        16: 'Storm',
        17: 'Light shower',
        18: 'Heavy shower'
    }

    headers = {
        'accept': 'application/json',
        'origin': 'https://www.bom.gov.au',
        'referer': 'https://www.bom.gov.au/',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }

    # Fetch 1-hourly data (temp, humidity, wind)
    hourly_url = 'https://api.bom.gov.au/apikey/v1/forecasts/1hourly/553/144?timezone=Australia%2FMelbourne'
    hourly_response = requests.get(hourly_url, headers=headers)
    hourly_data = hourly_response.json()

    # Fetch 3-hourly data (rain, UV, cloud cover)
    three_hourly_url = 'https://api.bom.gov.au/apikey/v1/forecasts/3hourly/553/144?timezone=Australia%2FMelbourne'
    three_hourly_response = requests.get(three_hourly_url, headers=headers)
    three_hourly_data = three_hourly_response.json()

    # Parse 1-hourly data
    hourly_records = []
    for day in hourly_data.get('fcst', []):
        for hour_data in day.get('1hourly', []):
            time_utc = hour_data['time_utc']
            dt = pd.to_datetime(time_utc).tz_convert('Australia/Melbourne')

            atm = hour_data.get('atm', {}).get('surf_air', {})
            wind = atm.get('wind', {})

            record = {
                'time_utc': time_utc,
                'Date': dt.strftime('%Y-%m-%d'),
                'Hour': dt.hour,
                'Temperature': int(round(atm.get('temp_cel', 0))),
                'Feels like': int(round(atm.get('temp_apparent_cel', 0))),
                'Humidity': int(round(atm.get('hum_relative_percent', 0))),
                'Wind_speed_kts': wind.get('speed_10m_avg_kts'),
                'Wind_direction': wind.get('dirn_10m_deg_t'),
                'Gust_kts': wind.get('gust_speed_10m_max_kts'),
                'Dew_point': atm.get('temp_dew_pt_cel'),
                'Mixing_height': wind.get('mixing_height_m')
            }
            hourly_records.append(record)

    hourly_df = pd.DataFrame(hourly_records)

    # Parse 3-hourly data
    three_hourly_records = []
    for day in three_hourly_data.get('fcst', []):
        for period_data in day.get('3hourly', []):
            start_time_utc = period_data['start_time_utc']
            dt = pd.to_datetime(start_time_utc).tz_convert('Australia/Melbourne')

            atm = period_data.get('atm', {}).get('surf_air', {})
            precip = atm.get('precip', {})
            weather = atm.get('weather', {})
            terr = period_data.get('terr', {}).get('surf_land', {})

            # Get weather description from icon code
            icon_code = weather.get('icon_code', 0)
            if icon_code is None:
                icon_code = 0
            icon_code = int(icon_code)
            summary = icon_descriptions.get(icon_code, '')

            record = {
                'time_utc': start_time_utc,
                'Summary': summary,
                'Rain - 50%': int(precip.get('exceeding_50percentchance_total_mm', 0)),
                'Rain - 25%': int(precip.get('exceeding_25percentchance_total_mm', 0)),
                'Rain - 10%': int(precip.get('exceeding_10percentchance_total_mm', 0)),
                'UV Index': int(atm.get('radiation', {}).get('uv_clear_sky_code', 0)),
                'Cloud cover': int(atm.get('cloud_amt_avg_percent', 0)),
                'Fire_danger': terr.get('fire_danger', {}).get('forest_fuel_dryness_factor_avg_code')
            }
            three_hourly_records.append(record)

    three_hourly_df = pd.DataFrame(three_hourly_records)

    # Merge dataframes - forward fill 3-hourly data to match hourly timestamps
    merged_df = hourly_df.copy()
    merged_df['time_utc'] = pd.to_datetime(merged_df['time_utc'])
    three_hourly_df['time_utc'] = pd.to_datetime(three_hourly_df['time_utc'])

    # Sort both by time
    merged_df = merged_df.sort_values('time_utc')
    three_hourly_df = three_hourly_df.sort_values('time_utc')

    # Merge and forward fill the 3-hourly data
    merged_df = pd.merge_asof(merged_df, three_hourly_df, on='time_utc', direction='backward')

    # Add scraped_datetime and dedup_key
    merged_df['scraped_datetime'] = format_scrape_time
    merged_df['dedup_key'] = merged_df['Date'].astype(str) + '_' + merged_df['Hour'].astype(str) + '_' + merged_df['scraped_datetime'].astype(str)

    # Save to parquet
    folder_path = os.path.join(pathos, 'data', 'melbs', 'hourly_forecasts')
    os.makedirs(folder_path, exist_ok=True)

    current_month = scrape_time.strftime('%Y-%m')
    filename = f"{current_month}.parquet"
    filepath = os.path.join(folder_path, filename)

    if os.path.exists(filepath):
        existing_df = pd.read_parquet(filepath)

        # Check if existing data needs cleaning (has string values in numeric columns)
        needs_cleaning = False
        if 'Temperature' in existing_df.columns:
            if existing_df['Temperature'].dtype == 'object':
                needs_cleaning = True

        if needs_cleaning:
            raise ValueError(
                "Existing parquet file contains old string format data. "
                "Please run clean_existing_parquet() from hourly_foreast.py first"
            )

        combined_df = pd.concat([existing_df, merged_df], ignore_index=True)
        combined_df = combined_df.drop_duplicates(subset=['dedup_key'], keep='last')
        combined_df = combined_df.sort_values(by=['Date', 'Hour'])
        combined_df.to_parquet(filepath, index=False)
    else:
        merged_df = merged_df.sort_values(by=['Date', 'Hour'])
        merged_df.to_parquet(filepath, index=False)

    # Always save CSV for inspection
    csv_filepath = filepath.replace('.parquet', '.csv')
    final_df = pd.read_parquet(filepath)
    final_df.to_csv(csv_filepath, index=False)

    # Create hourly_forecasts.json with today's data only
    today_date_str = scrape_time.strftime('%Y-%m-%d')
    today_df = merged_df[merged_df['Date'] == today_date_str].copy()

    if len(today_df) > 0:
        json_cols = ['Date', 'Hour', 'Summary', 'Temperature', 'Feels like',
                     'Rain - 50%', 'Rain - 25%', 'Rain - 10%',
                     'Humidity', 'UV Index', 'Cloud cover']

        json_df = today_df[json_cols].copy()
        # Fill any missing summaries with empty string
        json_df['Summary'] = json_df['Summary'].fillna('')
        json_output = json_df.to_dict('records')

        json_path = os.path.join(pathos, 'melbs', 'static', 'hourly_forecasts.json')
        with open(json_path, 'w') as f:
            json.dump(json_output, f, indent=2)

    return merged_df

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

fetch_hourly_forecast_api()


script_run_time = datetime.datetime.now(pytz.timezone("Australia/Melbourne"))
run_time_data = {
    "lastUpdated": script_run_time.isoformat()
}


run_time_file = "melbs/static/last_updated.json"
with open(run_time_file, 'w') as f:
    json.dump(run_time_data, f, indent=2)