import requests
import zipfile
import os
import shutil
import pandas as pd
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup

import pytz
today = datetime.now()
scrape_date_stemmo = today.astimezone(pytz.timezone("Australia/Brisbane")).strftime('%Y_%m_%d_%H')
current_year = today.year
p_c_value = -int(today.timestamp())  # Negative timestamp in seconds





def grab_melbs(bom_url, stemmo, value_column):
    # Create data/melbs directory
    output_dir = Path("data/melbs")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Download the zip file with proper headers
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }

    response = requests.get(bom_url, headers=headers)
    response.raise_for_status()

    # Save zip file temporarily
    zip_path = output_dir / "temp_weather_data.zip"
    with open(zip_path, 'wb') as f:
        f.write(response.content)

    # Check if response is actually a zip file
    if response.content[:4] != b'PK\x03\x04':  # ZIP file magic number
        print(f"Error: BOM returned HTML instead of ZIP file")
        print(f"URL used: {bom_url}")
        print(f"Response preview: {response.text[:500]}")
        raise ValueError("BOM service returned an error page instead of data")

    # Extract zip file to temporary location
    temp_dir = output_dir / "temp_extract"
    temp_dir.mkdir(exist_ok=True)

    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)

    # Find the CSV file and process it
    csv_files = list(temp_dir.glob("*.csv"))
    if csv_files:
        csv_file = csv_files[0]

        # Read and process the CSV
        df = pd.read_csv(csv_file)

        # Combine Year, Month, Day columns into Date
        df['Date'] = pd.to_datetime(df[['Year', 'Month', 'Day']])
        df['Date'] = df['Date'].dt.strftime('%Y-%m-%d')

        # Rename the specified column to 'Value'
        df = df.rename(columns={value_column: 'Value'})

        # Keep only Date and Value columns
        processed_df = df[['Date', 'Value']]

        # Save processed CSV
        final_csv = output_dir / f"{stemmo}.csv"
        processed_df.to_csv(final_csv, index=False)

        # Drop null values and save as JSON
        json_df = processed_df.dropna()
        json_dir = Path("melbs/static")
        json_dir.mkdir(parents=True, exist_ok=True)
        json_file = json_dir / f"historic_{stemmo}.json"
        json_df.to_json(json_file, orient='records', indent=2)

        print(f"Processed CSV saved as {final_csv}")
        print(f"JSON exported as {json_file}")
    else:
        print("No CSV file found in extracted data")

    # Clean up temporary files
    shutil.rmtree(temp_dir)
    os.remove(zip_path)


def fetch_climate_data():
    climate_url = "https://www.bom.gov.au/clim_data/cdio/tables/text/IDCJCM0035_086338.csv"

    # Create directories
    csv_dir = Path("data/melbs")
    csv_dir.mkdir(parents=True, exist_ok=True)

    json_dir = Path("melbs/static")
    json_dir.mkdir(parents=True, exist_ok=True)

    # Download headers
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }

    response = requests.get(climate_url, headers=headers)
    response.raise_for_status()

    # Find the header row and skip metadata
    lines = response.text.split('\n')

    # Find where the actual data starts (look for "Statistic Element" header)
    skip_rows = 0
    for i, line in enumerate(lines):
        if 'Statistic Element' in line:
            skip_rows = i
            break

    print(f"Skipping {skip_rows} rows to reach header")

    # Process the data starting from the header row
    processed_lines = lines[skip_rows:]
    processed_csv_content = '\n'.join(processed_lines)

    # Save processed CSV
    csv_file = csv_dir / "climate.csv"
    with open(csv_file, 'w') as f:
        f.write(processed_csv_content)

    # Read processed CSV and clean data
    df = pd.read_csv(csv_file)

    # Drop rows where most data columns are empty (keep only rows with actual data)
    # Count non-null values in data columns (excluding the first column which is the statistic name)
    data_columns = df.columns[1:]  # All columns except the first one
    df['non_null_count'] = df[data_columns].notna().sum(axis=1)

    # Keep rows that have at least some data (more than 2 non-null values in data columns)
    df_clean = df[df['non_null_count'] > 2].copy()
    df_clean = df_clean.drop('non_null_count', axis=1)

    # Save cleaned CSV
    df_clean.to_csv(csv_file, index=False)

    # Save as JSON
    json_file = json_dir / "climate.json"
    df_clean.to_json(json_file, orient='records', indent=2)

    print(f"Climate data saved as {csv_file}")
    print(f"Climate JSON exported as {json_file}")


def get_link(bom_page_url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }

    response = requests.get(bom_page_url, headers=headers)
    response.raise_for_status()

    soup = BeautifulSoup(response.content, 'html.parser')

    link = soup.find('a', string='All years of data')

    if link and link.get('href'):
        href = link.get('href')
        if href.startswith('http'):
            return href
        else:
            from urllib.parse import urljoin
            return urljoin(bom_page_url, href)

    return None


# bom_url = f"https://www.bom.gov.au/jsp/ncc/cdio/weatherData/av?p_display_type=dailyZippedDataFile&p_stn_num=086338&p_c=-1490983453&p_nccObsCode=136&p_startYear={current_year}"

bom_url = get_link('https://www.bom.gov.au/jsp/ncc/cdio/weatherData/av?p_nccObsCode=136&p_display_type=dailyDataFile&p_startYear=&p_c=&p_stn_num=086338')

grab_melbs(bom_url, "rain", "Rainfall amount (millimetres)")

# bom_url = f"https://www.bom.gov.au/jsp/ncc/cdio/weatherData/av?p_display_type=dailyZippedDataFile&p_stn_num=086338&p_c=-1490969851&p_nccObsCode=122&p_startYear={current_year}"
bom_url = get_link('https://www.bom.gov.au/jsp/ncc/cdio/weatherData/av?p_nccObsCode=122&p_display_type=dailyDataFile&p_startYear=&p_c=&p_stn_num=086338')
grab_melbs(bom_url, "temp", "Maximum temperature (Degree C)")

fetch_climate_data()



# linko = get_link('https://www.bom.gov.au/jsp/ncc/cdio/weatherData/av?p_nccObsCode=136&p_display_type=dailyDataFile&p_startYear=&p_c=&p_stn_num=086338')

# print(linko)