# %%
import pandas as pd
import os
import requests
from io import StringIO
from bs4 import BeautifulSoup as bs



import time

import datetime
import pytz

# %%

# from selenium import webdriver 
# from selenium.webdriver.firefox.options import Options
# from selenium.webdriver.support.ui import Select
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support import expected_conditions as EC

# chrome_options = Options()
# chrome_options.add_argument("--headless")

# driver = webdriver.Firefox(options=chrome_options)

# %%

today = datetime.datetime.now()
scrape_date_stemmo = today.astimezone(pytz.timezone("Australia/Brisbane")).strftime('%Y%m%d')
scrape_hour = today.astimezone(pytz.timezone("Australia/Brisbane")).strftime('%H')
today_for_loop = today.astimezone(pytz.timezone("Australia/Brisbane"))
# %%


def dumper(path, name, frame):
    with open(f'{path}/{name}.csv', 'w') as f:
        frame.to_csv(f, index=False, header=True)

def rand_delay(num):
  import random 
  import time 
  rando = random.random() * num
#   print(rando)
  time.sleep(rando)

def if_no_fold_create(pathos, to_check):
    if pathos[-1] != '/':
        pathos += '/'

    # Create parent directory if it doesn't exist
    os.makedirs(pathos, exist_ok=True)

    folds = os.listdir(pathos)

    if to_check not in folds:
        os.mkdir(f"{pathos}{to_check}")
    # print(folds)


# %%

def scraper(stem, out_path, combo_path, urlo):

    print("## Starting: ", stem)

    # rand_delay(10)

    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36",
    'Accept-Language': "en-GB,en-US;q=0.9,en;q=0.8",
    "Referer": 'https://www.google.com',
    "DNT":'1'}

    r = requests.get(urlo, headers=headers)


    # print("R status: ", r.status_code)
    tabs = pd.read_html(StringIO(r.text))[1:]

    # driver.get(urlo)

    time.sleep(2)

    # tabs = pd.read_html(driver.page_source)
    # print("Num tabs: ", len(tabs))


    if_no_fold_create('data/raw', scrape_date_stemmo)


    day_counter = 0

    listo = []

    for i in range(0, len(tabs)):

        # if tabs[i].columns.tolist() == ['Time (AEDT)', 'Temp (°C)', 'Feels Like (°C)', 'Humidity(%)', 'Wind Direction', 'Wind Speed (km/h) (knots)', 
        #                                 'Wind Gust (km/h) (knots)', 'Pressure (hPa)', 'Rainfall since 9 am (mm)']:

        if  'Temp (°C)' in tabs[i].columns.tolist():

            tabbo = tabs[i]
            'Time (AEDT)', 'Temp (°C)', 'Feels Like (°C)', 'Humidity(%)', 'Wind Direction', 
            'Wind Speed (km/h) (knots)', 'Wind Gust (km/h) (knots)', 
            'Pressure (hPa)', 'Rainfall since 9 am (mm)'

            inter_date = today  - datetime.timedelta(days=day_counter)
            inter_date_format = inter_date.astimezone(pytz.timezone("Australia/Brisbane")).strftime('%Y-%m-%d')

            tabbo['Date'] = inter_date_format

            # print(inter_date_format)

            dumper(f"{out_path}/{scrape_date_stemmo}", f"{stem}_{scrape_hour}_{day_counter}", tabbo)  
            listo.append(tabbo)  


            cat = pd.concat(listo)

            if os.path.isfile(f"{combo_path}/{stem}"):
                old = pd.read_csv(f"{combo_path}/{stem}")
                cat = pd.concat[old, cat]
                cat.drop_duplicates(subset=['Time (AEDT)', 'Date'], inplace=True)

            
            dumper(combo_path, stem, cat)

            # If stem is Melbourne, also save as observations.json
            if stem == "Melbourne":
                from pathlib import Path

                # Process Melbourne data for daily summaries
                melb_processed = cat.copy()

                # Group by Date and get daily summaries
                daily_summary = melb_processed.groupby('Date').agg({
                    'Temp (°C)': 'max',  # Max temp of the day
                    'Rainfall since 9 am (mm)': 'max',  # Cumulative rainfall
                    'Wind Speed (km/h) (knots)': lambda x: x.str.extract('(\d+)').astype(float).max() if x.notna().any() else None,  # Max wind speed
                    'Humidity(%)': 'mean'  # Average humidity
                }).reset_index()

                # Rename columns
                daily_summary = daily_summary.rename(columns={
                    'Date': 'Date',
                    'Temp (°C)': 'Temp',
                    'Rainfall since 9 am (mm)': 'Rain',
                    'Wind Speed (km/h) (knots)': 'Wind',
                    'Humidity(%)': 'Humidity'
                })

                # Drop rows with all null values for the weather data
                daily_summary = daily_summary.dropna(subset=['Temp', 'Rain', 'Wind', 'Humidity'], how='all')

                json_dir = Path("melbs/static")
                json_dir.mkdir(parents=True, exist_ok=True)
                json_file = json_dir / "observations.json"
                daily_summary.to_json(json_file, orient='records', indent=2)
                print(f"Melbourne daily summary saved as {json_file}")

            day_counter += 1
        # else:
        #     print(tabs[i].columns.tolist())
        #     print("Didn't work?")
        #     continue




# scraper("Sydney", 'data/raw','data',  'http://www.bom.gov.au/places/nsw/turramurra/observations/sydney---observatory-hill/')
scraper("Sydney", 'data/raw','data',  'https://www.bom.gov.au/weatherstation/australia/new-south-wales/66214/accessible-observations')

# https://www.bom.gov.au/location/australia/victoria/central/bvic_pt042-melbourne/accessible-forecast
# scraper("Melbourne", 'data/raw','data',  'http://www.bom.gov.au/places/vic/melbourne/observations/melbourne-(olympic-park)/')
# # scraper("Melbourne", 'data/raw','data',  'http://www.bom.gov.au/places/vic/melbourne/observations/melbourne-(olympic-park)/')

# scraper("Brisbane", 'data/raw','data',  'http://www.bom.gov.au/places/qld/brisbane/observations/brisbane/')

# scraper("Perth", 'data/raw','data',  'http://www.bom.gov.au/places/wa/perth/observations/perth/')

# scraper("Adelaide", 'data/raw','data',  'http://www.bom.gov.au/places/sa/adelaide/observations/adelaide-(west-terrace----ngayirdapira)/')

# scraper("Hobart", 'data/raw','data',  'http://www.bom.gov.au/places/tas/hobart/observations/hobart/')

# scraper("Canberra", 'data/raw','data',  'http://www.bom.gov.au/places/act/canberra/observations/canberra/')

# scraper("Darwin", 'data/raw','data',  'http://www.bom.gov.au/places/nt/darwin/')

# driver.quit()

# Save script run time to melbs/static
from pathlib import Path
import json

script_run_time = datetime.datetime.now(pytz.timezone("Australia/Melbourne"))
run_time_data = {
    "lastUpdated": script_run_time.isoformat()
}

json_dir = Path("melbs/static")
json_dir.mkdir(parents=True, exist_ok=True)
run_time_file = json_dir / "last_updated.json"
with open(run_time_file, 'w') as f:
    json.dump(run_time_data, f, indent=2)
# print(f"Script run time saved to {run_time_file}")

# %%

def forecast_scraper(urlo, stem, out_path):
    print("## Starting: ", stem)


    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36",
    'Accept-Language': "en-GB,en-US;q=0.9,en;q=0.8",
    "Referer": 'https://www.google.com',
    "DNT":'1'}

    r = requests.get(urlo, headers=headers)



    soup = bs(r.text, 'html.parser')

    container = soup.find("div", id='main-content')

    days = container.find_all(class_='day')

    records = []

    for i in range(len(days)):
        inter_date = today_for_loop + datetime.timedelta(days=i)
        inter_date = inter_date.strftime("%Y-%m-%d")
        # print(i, today_for_loop + datetime.timedelta(days=i))

        inter = days[i]
        rain = inter.find(class_='amt').text

        if "to" in rain:
            rain = int(rain.split("to")[-1].replace('mm', '').strip())
        else:
            rain = int(rain.replace('mm', '').strip())

        # print("rain: ", rain)
        max = int(inter.find(class_='max').text.replace('°C', ''))
        # print("max: ",  max)

        record = {"Date": inter_date, 'Max_temp': max, 'Rain': rain}
        records.append(record)

    cat = pd.DataFrame.from_records(records)

    dumper(out_path, scrape_date_stemmo, cat)

    json_file = "melbs/static/forecasts.json"
    cat.to_json(json_file, orient='records', indent=2)

# Only run forecast scraper once per day at 9am Brisbane time
if scrape_hour == '09':
    try:
        forecast_scraper('https://www.bom.gov.au/places/vic/melbourne/forecast/', "melbs", 'data/melbs/forecasts', )
    except Exception as e:
        print(f"Forecast scraper failed: {e}")
        pass

# %%
