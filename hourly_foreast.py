# %%
import pandas as pd
import os
import requests
from io import StringIO
import time
import json 
from bs4 import BeautifulSoup as bs

import datetime
import pytz
import pathlib
from playwright.sync_api import sync_playwright

pathos = pathlib.Path(__file__).parent
os.chdir(pathos)

today = datetime.datetime.now()
scrape_time = today.astimezone(pytz.timezone("Australia/Brisbane"))
format_scrape_time = datetime.datetime.strftime(scrape_time, "%Y_%m_%d_%H")

pub_scrape_time = datetime.datetime.strftime(scrape_time, "%-I:%M%p %d/%m")

# %%

thingo = "hourly-weather-table bom-table bom-table--scrollable bom-table--more-right"

# r = requests.get('https://www.bom.gov.au/location/australia/victoria/central/bvic_pt042-melbourne/accessible-forecast')

# soup = bs(r.text, 'html.parser')


def rand_delay(num):
  import random 
  import time 
  rando = random.random() * num
#   print(rando)
  time.sleep(rando)

# %%

# tabs = soup.find(class_='hourly-weather-table')

# print(tabs)

def hourly_forecast(urlo, javascript_code, awaito):
    tries = 0
    with sync_playwright() as p:
        try:
            browser = p.firefox.launch()
            context = browser.new_context()
            page = context.new_page()
            page.goto(urlo)

            waiting_around = page.locator(awaito).first
            waiting_around.wait_for()

            # Click all "Show all" labels to ensure all columns are visible in all tables
            try:
                show_all_labels = page.locator('label[for^="SHOW_ALL_FORECAST_TABS"]')
                count = show_all_labels.count()
                for i in range(count):
                    try:
                        show_all_labels.nth(i).click(timeout=5000)
                    except:
                        pass
                page.wait_for_timeout(2000)
            except:
                pass

            resulto = page.evaluate(javascript_code)
            browser.close()

            frame = pd.DataFrame.from_records(resulto)
            frame['scraped_datetime'] = format_scrape_time

            # Parse the Time column to extract date and hour
            today_date = scrape_time.date()

            # Extract hour and period from Time column
            frame['hour_str'] = frame['Time'].str.extract(r'(\d+)')[0].astype(int)
            frame['period'] = frame['Time'].str.extract(r'(am|pm)')[0]

            # Convert to 24-hour format
            frame['Hour'] = frame.apply(lambda row:
                row['hour_str'] if row['period'] == 'am' and row['hour_str'] != 12
                else 0 if row['period'] == 'am' and row['hour_str'] == 12
                else row['hour_str'] + 12 if row['period'] == 'pm' and row['hour_str'] != 12
                else 12,
                axis=1
            )

            # Determine the date for each forecast
            dates = []
            current_date = today_date
            last_hour = -1

            for hour in frame['Hour']:
                if hour < last_hour:
                    current_date = current_date + datetime.timedelta(days=1)
                dates.append(current_date.strftime('%Y-%m-%d'))
                last_hour = hour

            frame['Date'] = dates
            frame = frame.drop(columns=['hour_str', 'period'])

            # Save to parquet
            folder_path = os.path.join(pathos, 'data', 'melbs', 'hourly_forecasts')
            os.makedirs(folder_path, exist_ok=True)

            current_month = scrape_time.strftime('%Y-%m')
            filename = f"{current_month}.parquet"
            filepath = os.path.join(folder_path, filename)

            frame['dedup_key'] = frame['Date'].astype(str) + '_' + frame['Hour'].astype(str) + '_' + frame['scraped_datetime'].astype(str)

            if os.path.exists(filepath):
                existing_df = pd.read_parquet(filepath)
                combined_df = pd.concat([existing_df, frame], ignore_index=True)
                combined_df = combined_df.drop_duplicates(subset=['dedup_key'], keep='last')
                combined_df = combined_df.sort_values(by=['Date', 'Hour'])
                combined_df.to_parquet(filepath, index=False)
            else:
                frame = frame.sort_values(by=['Date', 'Hour'])
                frame.to_parquet(filepath, index=False)

            # Create hourly_forecasts.json with today's data only
            today_date_str = scrape_time.strftime('%Y-%m-%d')
            today_df = frame[frame['Date'] == today_date_str].copy()

            if len(today_df) > 0:
                json_cols = ['Date', 'Hour', 'Summary', 'Temperature', 'Feels like',
                             'Rain - 50% (medium) chance of at least',
                             'Rain - 25% (low) chance of at least',
                             'Rain - 10% (very low) chance of at least',
                             'Humidity', 'UV Index', 'Cloud cover']

                json_df = today_df[json_cols].copy()
                json_df = json_df.fillna(method='ffill')

                # Clean rain columns - extract just the number
                rain_cols = ['Rain - 50% (medium) chance of at least',
                             'Rain - 25% (low) chance of at least',
                             'Rain - 10% (very low) chance of at least']

                for col in rain_cols:
                    # Extract first number found, or 0 if no number
                    json_df[col] = json_df[col].astype(str).str.extract(r'(\d+)', expand=False).fillna('0').astype(int)

                # Rename rain columns
                json_df = json_df.rename(columns={
                    'Rain - 50% (medium) chance of at least': 'Rain - 50%',
                    'Rain - 25% (low) chance of at least': 'Rain - 25%',
                    'Rain - 10% (very low) chance of at least': 'Rain - 10%'
                })

                # Convert to integers
                json_df['Temperature'] = json_df['Temperature'].str.replace('°', '').astype(int)
                json_df['Feels like'] = json_df['Feels like'].str.replace('°', '').astype(int)
                json_df['Humidity'] = json_df['Humidity'].astype(str).str.extract(r'(\d+)', expand=False).fillna('0').astype(int)
                json_df['UV Index'] = json_df['UV Index'].astype(str).str.extract(r'(\d+)', expand=False).fillna('0').astype(int)
                json_df['Cloud cover'] = json_df['Cloud cover'].astype(str).str.extract(r'(\d+)', expand=False).fillna('0').astype(int)

                json_output = json_df.to_dict('records')

                json_path = os.path.join(pathos, 'melbs', 'static', 'hourly_forecasts.json')
                with open(json_path, 'w') as f:
                    json.dump(json_output, f, indent=2)

            return frame

        except Exception as e:
            tries += 1
            browser.close()
            rand_delay(5)
            if e == 'Timeout 30000ms exceeded.' and tries <= 3:
                hourly_forecast(urlo, javascript_code, awaito)


stringo = """  var tables = document.querySelectorAll('.hourly-weather-table');

  Array.from(tables).flatMap(table => {
      // Get headers from thead
      var headers = Array.from(table.querySelectorAll('thead th')).map(th => th.innerText.trim());

      var tbody = table.querySelector('tbody');
      var rows = Array.from(tbody.querySelectorAll('tr'));

      // Track which columns are occupied by rowspan cells
      var rowspanTracker = [];

      return rows.map((row, rowIndex) => {
          let data = {};

          // Initialize rowspan tracker for this row
          if (!rowspanTracker[rowIndex]) {
              rowspanTracker[rowIndex] = [];
          }

          // Get time from first cell (th)
          let timeCell = row.querySelector('th');
          if (timeCell) {
              data['Time'] = timeCell.innerText.trim();
          }

          // Get all td cells in this row
          let cells = Array.from(row.querySelectorAll('td'));

          // Map cells to headers, accounting for rowspan
          let headerIndex = 1; // Start at 1 to skip "Time" header
          let cellIndex = 0;

          while (cellIndex < cells.length && headerIndex < headers.length) {
              // Skip headers that are occupied by rowspan from previous rows
              while (rowspanTracker[rowIndex] && rowspanTracker[rowIndex][headerIndex]) {
                  headerIndex++;
              }

              if (headerIndex >= headers.length) break;

              let cell = cells[cellIndex];
              let rowspan = parseInt(cell.getAttribute('rowspan') || '1');

              // Store data for this cell
              data[headers[headerIndex]] = cell.innerText.trim();

              // Track rowspan for future rows
              if (rowspan > 1) {
                  for (let i = 1; i < rowspan; i++) {
                      let futureRow = rowIndex + i;
                      if (!rowspanTracker[futureRow]) {
                          rowspanTracker[futureRow] = [];
                      }
                      rowspanTracker[futureRow][headerIndex] = true;
                  }
              }

              cellIndex++;
              headerIndex++;
          }

          return data;
      });
  });"""

def clean_existing_parquet():
    """
    One-time cleanup of existing parquet file to convert string values to integers.
    """
    folder_path = os.path.join(pathos, 'data', 'melbs', 'hourly_forecasts')
    current_month = scrape_time.strftime('%Y-%m')
    filename = f"{current_month}.parquet"
    filepath = os.path.join(folder_path, filename)

    if os.path.exists(filepath):
        df = pd.read_parquet(filepath)

        # Clean and ensure integer columns are int type
        int_cols = ['Temperature', 'Feels like', 'Humidity', 'Hour', 'Rain - 50%', 'Rain - 25%', 'Rain - 10%', 'UV Index', 'Cloud cover']
        for col in int_cols:
            if col in df.columns:
                # Convert to string, extract first number, fill NaN with 0, then convert to int
                df[col] = pd.to_numeric(
                    df[col].astype(str).str.extract(r'(\d+)', expand=False).fillna('0'),
                    errors='coerce'
                ).fillna(0).astype(int)

        # Save cleaned data back
        df.to_parquet(filepath, index=False)
        # Also save as CSV
        csv_filepath = filepath.replace('.parquet', '.csv')
        df.to_csv(csv_filepath, index=False)
        print(f"Cleaned parquet file: {filepath}")
    else:
        print(f"No existing parquet file found at {filepath}")

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
                "Please run clean_existing_parquet() first by uncommenting line 417 in hourly_foreast.py"
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

# hourly_forecast('https://www.bom.gov.au/location/australia/victoria/central/bvic_pt042-melbourne/accessible-forecast',
#              stringo,
#              '.hourly-weather-table'
#              )

# Run once to clean existing parquet file with old string format
# clean_existing_parquet()

# Run regularly to fetch new data
fetch_hourly_forecast_api()




# curl 'https://api.bom.gov.au/apikey/v1/forecasts/1hourly/553/144?timezone=Australia%2FMelbourne' \
#   -H 'accept: application/json, */*;q=0.8' \
#   -H 'accept-language: en-GB,en-US;q=0.9,en;q=0.8' \
#   -H 'if-none-match: "0776929c5b0441c423e39f0773b580c76"' \
#   -H 'origin: https://www.bom.gov.au' \
#   -H 'priority: u=1, i' \
#   -H 'referer: https://www.bom.gov.au/' \
#   -H 'sec-ch-ua: "Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"' \
#   -H 'sec-ch-ua-mobile: ?0' \
#   -H 'sec-ch-ua-platform: "macOS"' \
#   -H 'sec-fetch-dest: empty' \
#   -H 'sec-fetch-mode: cors' \
#   -H 'sec-fetch-site: same-site' \
#   -H 'user-agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'


# curl 'https://api.bom.gov.au/apikey/v1/forecasts/3hourly/553/144?timezone=Australia%2FMelbourne' \
#   -H 'accept: application/json, */*;q=0.8' \
#   -H 'accept-language: en-GB,en-US;q=0.9,en;q=0.8' \
#   -H 'if-none-match: "0d656516da573b6a6e261b67b896f6562"' \
#   -H 'origin: https://www.bom.gov.au' \
#   -H 'priority: u=1, i' \
#   -H 'referer: https://www.bom.gov.au/' \
#   -H 'sec-ch-ua: "Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"' \
#   -H 'sec-ch-ua-mobile: ?0' \
#   -H 'sec-ch-ua-platform: "macOS"' \
#   -H 'sec-fetch-dest: empty' \
#   -H 'sec-fetch-mode: cors' \
#   -H 'sec-fetch-site: same-site' \
#   -H 'user-agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'


# curl 'https://api.bom.gov.au/apikey/v1/forecasts/daily/553/144?timezone=Australia%2FMelbourne' \
#   -H 'sec-ch-ua-platform: "macOS"' \
#   -H 'Referer: https://www.bom.gov.au/' \
#   -H 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36' \
#   -H 'Accept: application/json, */*;q=0.8' \
#   -H 'sec-ch-ua: "Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"' \
#   -H 'sec-ch-ua-mobile: ?0'