# %%
import pandas as pd 
import os 
import pathlib
# pd.set_option("display.max_rows", 100)

from sudulunu.helpers import pp, make_num, dumper
# from sudulunu.helpers import rand_delay, unique_in_col, null_in_col
# from sudulunu.helpers import combine_from_folder

# %%



pathos = pathlib.Path(__file__).parent
os.chdir(pathos)


#%%

def combine_from_folder(stemmo, pathos):
  
    listo = []

    foldos = os.listdir(pathos)

    foldos = [pathos + x for x in foldos if x != '.DS_Store']
    for foldo in foldos:
        fillos = os.listdir(foldo)
        fillos = [foldo + '/' + x for x in fillos if x != '.DS_Store']
        fillos = [x for x in fillos if stemmo in x]
        # print(fillos)
        for fillo in fillos:
            # print(fillo)

            inter = pd.read_csv(fillo)
            # inter['City'] = stemmo

            listo.append(inter)

    cat = pd.concat(listo)

    return cat

for city in ['Adelaide', 'Brisbane', 'Canberra', 'Hobart', 'Melbourne', 'Perth', 'Sydney']:

    print(city)
    data = combine_from_folder(city, 'data/raw/')

    df = data.copy()

    # print(len(df))
    df.sort_values(by=['Date'], ascending=False, inplace=True)
    timeo = [x for x in df.columns.tolist() if "time" in x.lower()][0]
    df.drop_duplicates(subset=[timeo, 'Date'], keep='first', inplace=True)

    print(len(df))

    # print(df['Date'].min())
    # print(df['Date'].max())

    dumper('data', city, df)
# pp(df)


#%%

# Process historic regional data for Melbourne
def process_historic_regional():
    """Process historic regional rainfall and temperature data"""

    # Process rainfall data (IDCJAC0009)
    rain_file = 'data/historic_regional/IDCJAC0009_086071_1800/IDCJAC0009_086071_1800_Data.csv'
    if os.path.exists(rain_file):
        df_rain = pd.read_csv(rain_file)
        df_rain['Date'] = pd.to_datetime(df_rain[['Year', 'Month', 'Day']])
        df_rain['Date'] = df_rain['Date'].dt.strftime('%Y-%m-%d')
        df_rain = df_rain.rename(columns={'Rainfall amount (millimetres)': 'Value'})
        df_rain = df_rain[['Date', 'Value']].dropna()

        # Save to melbs/static
        df_rain.to_json('melbs/static/historic_rain.json', orient='records', indent=2)
        print(f"Processed historic rainfall: {len(df_rain)} records")

    # Process temperature data (IDCJAC0010)
    temp_file = 'data/historic_regional/IDCJAC0010_086071_1800/IDCJAC0010_086071_1800_Data.csv'
    if os.path.exists(temp_file):
        df_temp = pd.read_csv(temp_file)
        df_temp['Date'] = pd.to_datetime(df_temp[['Year', 'Month', 'Day']])
        df_temp['Date'] = df_temp['Date'].dt.strftime('%Y-%m-%d')
        df_temp = df_temp.rename(columns={'Maximum temperature (Degree C)': 'Value'})
        df_temp = df_temp[['Date', 'Value']].dropna()

        # Save to melbs/static
        df_temp.to_json('melbs/static/historic_temp.json', orient='records', indent=2)
        print(f"Processed historic temperature: {len(df_temp)} records")

process_historic_regional()

#%%