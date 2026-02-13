#!/usr/bin/env python3
"""
Convert old Melbourne CSV data from data/Old to monthly parquet files for data/new/Melbourne
"""

import pandas as pd
import os
from datetime import datetime
import glob

# Mapping from old CSV format to new BOM format
def convert_old_to_new_format(df):
    """
    Convert old CSV format to match BOM API format for compatibility with save_data function
    """
    # Create a new dataframe with BOM API column names
    new_df = pd.DataFrame()

    # Parse time and date to create full timestamp
    # Time format: "6:00 am" -> need to convert to 24hr
    # Date format: "2023-08-24"
    # Column name can be "Time (AEST)" or "Time (AEDT)"

    time_column = None
    for col in ['Time (AEST)', 'Time (AEDT)']:
        if col in df.columns:
            time_column = col
            break

    if time_column is None:
        raise ValueError(f"No time column found. Columns: {df.columns.tolist()}")

    def parse_time_to_hour(time_str):
        """Convert '6:00 am' to hour number"""
        time_str = str(time_str).strip()

        # Handle NaN/None values
        if time_str == 'nan' or time_str == 'None' or time_str == '':
            return None

        parts = time_str.replace('am', '').replace('pm', '').strip().split(':')
        try:
            hour = int(parts[0])
        except (ValueError, IndexError):
            return None

        is_pm = 'pm' in time_str.lower()

        if is_pm and hour != 12:
            hour += 12
        elif not is_pm and hour == 12:
            hour = 0

        return hour

    # Create timestamp columns
    df['hour'] = df[time_column].apply(parse_time_to_hour)

    # Filter out rows with null hours (invalid time data)
    df = df[df['hour'].notna()].copy()

    df['datetime'] = pd.to_datetime(df['Date'] + ' ' + df['hour'].astype(int).astype(str) + ':00', format='%Y-%m-%d %H:%M')

    # Create local_date_time_full column (format: YYYYMMDDHHMMSS)
    new_df['local_date_time_full[80]'] = df['datetime'].dt.strftime('%Y%m%d%H%M%S')

    # Create local_date_time column (format: DD/HH:MMam/pm)
    def format_local_date_time(dt):
        day = dt.day
        hour = dt.hour
        if hour == 0:
            return f"{day:02d}/12:00am"
        elif hour < 12:
            return f"{day:02d}/{hour}:00am"
        elif hour == 12:
            return f"{day:02d}/12:00pm"
        else:
            return f"{day:02d}/{hour-12}:00pm"

    new_df['local_date_time[80]'] = df['datetime'].apply(format_local_date_time)

    # Map temperature columns
    new_df['air_temp'] = pd.to_numeric(df['Temp (°C)'], errors='coerce')
    new_df['apparent_t'] = pd.to_numeric(df['Feels Like (°C)'], errors='coerce')
    new_df['rel_hum'] = pd.to_numeric(df['Humidity(%)'], errors='coerce')

    # Map wind columns (need to split "7 4" into separate km/h and knots)
    df['wind_kmh'] = df['Wind Speed (km/h) (knots)'].str.extract(r'(\d+)').astype(float)
    df['wind_kt'] = df['Wind Speed (km/h) (knots)'].str.extract(r'\d+\s+(\d+)').astype(float)

    new_df['wind_dir[80]'] = df['Wind Direction']
    new_df['wind_spd_kmh'] = df['wind_kmh']
    new_df['wind_spd_kt'] = df['wind_kt']

    # Map gust columns
    df['gust_kmh'] = df['Wind Gust (km/h) (knots)'].str.extract(r'(\d+)').astype(float)
    df['gust_kt'] = df['Wind Gust (km/h) (knots)'].str.extract(r'\d+\s+(\d+)').astype(float)

    new_df['gust_kmh'] = df['gust_kmh']
    new_df['gust_kt'] = df['gust_kt']

    # Map pressure and rain
    new_df['press_qnh'] = pd.to_numeric(df['Pressure (hPa)'], errors='coerce')
    new_df['rain_trace[80]'] = pd.to_numeric(df['Rainfall since 9 am (mm)'], errors='coerce')

    # Add placeholder columns that might be in BOM data but not in old format
    new_df['sort_order'] = 0
    new_df['wmo'] = 95936  # Melbourne Olympic Park
    new_df['name[80]'] = 'Melbourne (Olympic Park)'
    new_df['lat'] = -37.8
    new_df['lon'] = 145.0

    return new_df


def process_old_data(old_data_path='data/Old', output_path='data/new/Melbourne'):
    """
    Process all old Melbourne CSV files and create monthly parquet files
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_path, exist_ok=True)

    # Get all date folders (YYYYMMDD format)
    date_folders = sorted([d for d in os.listdir(old_data_path)
                          if os.path.isdir(os.path.join(old_data_path, d)) and d.isdigit()])

    print(f"Found {len(date_folders)} date folders")

    # Group by month
    monthly_data = {}

    for date_folder in date_folders:
        folder_path = os.path.join(old_data_path, date_folder)

        # Get all Melbourne CSV files in this folder
        melbourne_files = glob.glob(os.path.join(folder_path, 'Melbourne_*.csv'))

        if not melbourne_files:
            continue

        # Parse date to get year-month
        try:
            date = datetime.strptime(date_folder, '%Y%m%d')
            year_month = date.strftime('%Y-%m')

            # Only process October 2025
            if year_month != '2025-10':
                continue
        except:
            print(f"Skipping invalid date folder: {date_folder}")
            continue

        # Read and combine all Melbourne files from this date
        date_dfs = []
        for csv_file in melbourne_files:
            try:
                df = pd.read_csv(csv_file)
                date_dfs.append(df)
            except Exception as e:
                print(f"Error reading {csv_file}: {e}")
                continue

        if date_dfs:
            # Combine all CSVs from this date
            combined_df = pd.concat(date_dfs, ignore_index=True)

            # Add to monthly data
            if year_month not in monthly_data:
                monthly_data[year_month] = []
            monthly_data[year_month].append(combined_df)

            print(f"Processed {date_folder} ({len(combined_df)} rows) -> {year_month}")

    # Now save each month as a parquet file
    print(f"\nCreating parquet files for {len(monthly_data)} months...")

    for year_month, month_dfs in sorted(monthly_data.items()):
        # Combine all data for this month
        month_df = pd.concat(month_dfs, ignore_index=True)

        # Convert to new format
        new_format_df = convert_old_to_new_format(month_df)

        # Drop duplicates
        new_format_df = new_format_df.drop_duplicates(subset=['local_date_time_full[80]'], keep='last')

        # Sort by timestamp
        new_format_df = new_format_df.sort_values(by='local_date_time_full[80]')

        # Save to parquet
        output_file = os.path.join(output_path, f'{year_month}.parquet')
        new_format_df.to_parquet(output_file, index=False)

        print(f"Created {output_file} ({len(new_format_df)} rows)")

    print(f"\nDone! Created {len(monthly_data)} parquet files in {output_path}")


if __name__ == '__main__':
    process_old_data()
