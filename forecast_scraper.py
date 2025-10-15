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

today = datetime.datetime.now()
scrape_date_stemmo = today.astimezone(pytz.timezone("Australia/Brisbane")).strftime('%Y%m%d')
scrape_hour = today.astimezone(pytz.timezone("Australia/Brisbane")).strftime('%H')

today_for_loop = today.astimezone(pytz.timezone("Australia/Brisbane"))


# %%

urlo = 'https://www.bom.gov.au/places/vic/melbourne/forecast/'
stem = 'melbs'

def dumper(path, name, frame):
    with open(f'{path}/{name}.csv', 'w') as f:
        frame.to_csv(f, index=False, header=True)

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

        print("rain: ", rain)
        max = int(inter.find(class_='max').text.replace('°C', ''))
        print("max: ",  max)

        record = {"Date": inter_date, 'Max_temp': max, 'Rain': rain}
        records.append(record)

    cat = pd.DataFrame.from_records(records)

    dumper(out_path, scrape_date_stemmo, cat)

    json_file = "melbs/static/forecasts.json"
    cat.to_json(json_file, orient='records', indent=2)

forecast_scraper('https://www.bom.gov.au/places/vic/melbourne/forecast/', "melbs", 'data/melbs/forecasts', )

    # print(days[i])



# print(days[0])


# %%
