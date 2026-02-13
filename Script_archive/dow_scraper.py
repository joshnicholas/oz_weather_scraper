# %%
import pandas as pd 
import os 
import requests

import time 

import datetime
import pytz


# %%

today = datetime.datetime.now()
scrape_date_stemmo = today.astimezone(pytz.timezone("Australia/Brisbane")).strftime('%Y%m%d')
scrape_hour = today.astimezone(pytz.timezone("Australia/Brisbane")).strftime('%H')

# %%

def if_no_fold_create(pathos, to_check):
    if pathos[-1] != '/':
        pathos += '/'

    folds = os.listdir(pathos)

    if to_check not in folds:
        os.mkdir(f"{pathos}{to_check}")

# %%

### Get the date range

months = [today - datetime.timedelta(days=(30 * x)) for x in range(0, 14)]
months = [x.strftime("%Y%m") for x in months]

# %%


cities = [("Sydney", 'http://www.bom.gov.au/climate/dwo/IDCJDW2124.'),
          ("Canberra", 'http://www.bom.gov.au/climate/dwo/IDCJDW2801.'),
          ("Melbourne", 'http://www.bom.gov.au/climate/dwo/IDCJDW3033.'),
          ("Brisbane", 'http://www.bom.gov.au/climate/dwo/IDCJDW4019.'),
          ("Adelaide", 'http://www.bom.gov.au/climate/dwo/IDCJDW5081.'),
          ("Perth", 'http://www.bom.gov.au/climate/dwo/IDCJDW6111.'),
          ("Hobart", 'http://www.bom.gov.au/climate/dwo/IDCJDW7021.'),
          ("Darwin", 'http://www.bom.gov.au/climate/dwo/IDCJDW8014.')]

cities = cities[:1]
months = months[:1]

print(months)
print(cities)

headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36",
'Accept-Language': "en-GB,en-US;q=0.9,en;q=0.8",
"Referer": 'https://www.google.com',
"DNT":'1'}

for city in cities:
    
    seat = city[0]
    

    for month in months:

        urlo = f"{city[1]}{month}.shtml"

        urlo = urlo.replace("http://www.bom.gov.au/climate/dwo/", f'http://www.bom.gov.au/climate/dwo/{month}/html/')

        r = requests.get(urlo, headers=headers)

        print(r.url)
        # print(r.status_code)

# %%


tabs = pd.read_html(r.text)[0]
tabs = tabs[[('Date', 'Date', 'Date'), ('Day', 'Day', 'Day'), ('Temps', 'Min', '°C'), ('Temps', 'Max', '°C'),]]
print(tabs)
print(tabs.columns.tolist())


# %%

# http://www.bom.gov.au/climate/dwo/{month}/html/