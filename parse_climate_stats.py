#!/usr/bin/env python3
"""
Parse climate statistics for Melbourne Olympic Park and save to JSON.
This script manually extracts climate statistics from BOM data.
"""

import json
from pathlib import Path

# Climate statistics for Melbourne Olympic Park
# Source: Bureau of Meteorology climate data
climate_stats = [
    {
        "Category": "Temperature",
        "Metric": "Mean_Max_Temp",
        "January": 25.9,
        "February": 25.9,
        "March": 23.9,
        "April": 20.3,
        "May": 16.7,
        "June": 14.1,
        "July": 13.5,
        "August": 15.0,
        "September": 17.3,
        "October": 19.7,
        "November": 22.0,
        "December": 24.2
    },
    {
        "Category": "Temperature",
        "Metric": "Mean_Min_Temp",
        "January": 14.3,
        "February": 14.6,
        "March": 13.3,
        "April": 10.8,
        "May": 8.7,
        "June": 6.9,
        "July": 6.0,
        "August": 6.7,
        "September": 8.0,
        "October": 9.6,
        "November": 11.3,
        "December": 13.0
    },
    {
        "Category": "Rainfall",
        "Metric": "Mean_Rainfall",
        "January": 46.8,
        "February": 48.0,
        "March": 50.1,
        "April": 57.3,
        "May": 55.7,
        "June": 49.5,
        "July": 47.5,
        "August": 50.0,
        "September": 58.0,
        "October": 66.0,
        "November": 60.3,
        "December": 59.1
    },
    {
        "Category": "Rainfall",
        "Metric": "Median_Rainfall",
        "January": 36.6,
        "February": 32.6,
        "March": 38.8,
        "April": 49.8,
        "May": 54.9,
        "June": 43.2,
        "July": 44.4,
        "August": 49.2,
        "September": 52.9,
        "October": 65.6,
        "November": 53.8,
        "December": 51.5
    },
    {
        "Category": "Rainfall",
        "Metric": "Decile_1",
        "January": 9.4,
        "February": 6.9,
        "March": 11.8,
        "April": 17.8,
        "May": 21.3,
        "June": 25.6,
        "July": 22.0,
        "August": 23.6,
        "September": 27.9,
        "October": 26.9,
        "November": 21.7,
        "December": 17.6
    },
    {
        "Category": "Rainfall",
        "Metric": "Decile_9",
        "January": 99.2,
        "February": 107.9,
        "March": 104.6,
        "April": 114.4,
        "May": 91.0,
        "June": 85.6,
        "July": 72.1,
        "August": 77.7,
        "September": 92.4,
        "October": 111.2,
        "November": 114.5,
        "December": 110.2
    },
    {
        "Category": "Humidity",
        "Metric": "Mean_9am_RH",
        "January": 63.0,
        "February": 66.0,
        "March": 68.0,
        "April": 71.0,
        "May": 77.0,
        "June": 80.0,
        "July": 79.0,
        "August": 73.0,
        "September": 67.0,
        "October": 62.0,
        "November": 63.0,
        "December": 62.0
    },
    {
        "Category": "Humidity",
        "Metric": "Mean_3pm_RH",
        "January": 47.0,
        "February": 48.0,
        "March": 49.0,
        "April": 52.0,
        "May": 59.0,
        "June": 63.0,
        "July": 61.0,
        "August": 56.0,
        "September": 53.0,
        "October": 50.0,
        "November": 49.0,
        "December": 47.0
    },
    {
        "Category": "Wind",
        "Metric": "Mean_9am_Wind",
        "January": 20.0,
        "February": 19.0,
        "March": 19.0,
        "April": 19.0,
        "May": 19.0,
        "June": 20.0,
        "July": 22.0,
        "August": 22.0,
        "September": 22.0,
        "October": 22.0,
        "November": 22.0,
        "December": 21.0
    }
]

# Save to JSON file
json_dir = Path("melbs/static")
json_dir.mkdir(parents=True, exist_ok=True)
json_file = json_dir / "climate_stats.json"

with open(json_file, 'w') as f:
    json.dump(climate_stats, f, indent=2)

print(f"Climate statistics saved to {json_file}")
