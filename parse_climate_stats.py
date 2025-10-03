#!/usr/bin/env python3
"""
Parse climate statistics for Melbourne Olympic Park from BOM HTML table and save to JSON.
"""

import json
import pandas as pd
from pathlib import Path
from io import StringIO

# HTML table content
html_table = """
<table summary="Complete available climate statistics for the selected Bureau of Meteorologe site. Columns contain monthly and annual statistics for various climate elements, as well as supporting information. Some formatting code is included for printing" class="statsdata" border="1" cellpadding="0" width="100%" id="statstable">
<colgroup><col id="firstcol"></colgroup>
<colgroup span="15"></colgroup>
<colgroup class="no-print"> <col class="no-print"><col class="no-print"></colgroup>
<thead>
<tr>
<th class="screentitletop" scope="col" width="100%">Statistics</th>
<th scope="col"><abbr title="January">Jan</abbr></th>
<th scope="col"><abbr title="February">Feb</abbr></th>
<th scope="col"><abbr title="March">Mar</abbr></th>
<th scope="col"><abbr title="April">Apr</abbr></th>
<th scope="col">May</th>
<th scope="col"><abbr title="June">Jun</abbr></th>
<th scope="col"><abbr title="July">Jul</abbr></th>
<th scope="col"><abbr title="August">Aug</abbr></th>
<th scope="col"><abbr title="September">Sep</abbr></th>
<th scope="col"><abbr title="October">Oct</abbr></th>
<th scope="col"><abbr title="November">Nov</abbr></th>
<th scope="col"><abbr title="December">Dec</abbr></th>
<th scope="col">Annual</th>
<th scope="col" colspan="2" width="8%"><abbr title="Years of available data">Years</abbr></th>
<th class="nographcell" scope="col" width="21">Plot</th>
<th class="nographcell" scope="col" width="21">Map</th>
</tr>
</thead>
<tbody>
<tr><td><a href="/climate/cdo/about/definitionstemp.shtml#meanmaxtemp">Mean  maximum temperature (°C)</a> </td><td class="highest">25.9</td><td class="highest">25.9</td><td>23.9</td><td>20.3</td><td>16.7</td><td>14.1</td><td class="lowest">13.5</td><td>15.0</td><td>17.3</td><td>19.7</td><td>22.0</td><td>24.2</td><td>19.9</td><td>160</td><td>1855<br>2014</td></tr>
<tr><td><a href="/climate/cdo/about/definitionstemp.shtml#meanmintemp">Mean minimum temperature (°C)</a></td><td>14.3</td><td class="highest">14.6</td><td>13.3</td><td>10.8</td><td>8.7</td><td>6.9</td><td class="lowest">6.0</td><td>6.7</td><td>8.0</td><td>9.6</td><td>11.3</td><td>13.0</td><td>10.3</td><td>160</td><td>1855<br>2014</td></tr>
<tr><td><a href="/climate/cdo/about/definitionsrain.shtml#meanrainfall">Mean rainfall (mm) </a></td><td class="lowest">46.8</td><td>48.0</td><td>50.1</td><td>57.3</td><td>55.7</td><td>49.5</td><td>47.5</td><td>50.0</td><td>58.0</td><td class="highest">66.0</td><td>60.3</td><td>59.1</td><td>648.3</td><td>160</td><td>1855<br>2015</td></tr>
<tr><td><a href="/climate/cdo/about/definitionsrain.shtml#decile5rainfall">Decile 5 (median) rainfall (mm) </a></td><td>36.6</td><td class="lowest">32.6</td><td>38.8</td><td>49.8</td><td>54.9</td><td>43.2</td><td>44.4</td><td>49.2</td><td>52.9</td><td class="highest">65.6</td><td>53.8</td><td>51.5</td><td>&nbsp;</td><td>160</td><td>n/a<br>n/a</td></tr>
<tr><td><a href="/climate/cdo/about/definitionsrain.shtml#decile1rainfall">Decile 1 rainfall (mm) </a></td><td>9.4</td><td class="lowest">6.9</td><td>11.8</td><td>17.8</td><td>21.3</td><td>25.6</td><td>22.0</td><td>23.6</td><td class="highest">27.9</td><td>26.9</td><td>21.7</td><td>17.6</td><td>&nbsp;</td><td>160</td><td>n/a<br>n/a</td></tr>
<tr><td><a href="/climate/cdo/about/definitionsrain.shtml#decile9rainfall">Decile 9 rainfall (mm) </a></td><td>99.2</td><td>107.9</td><td>104.6</td><td>114.4</td><td>91.0</td><td>85.6</td><td class="lowest">72.1</td><td>77.7</td><td>92.4</td><td>111.2</td><td class="highest">114.5</td><td>110.2</td><td>&nbsp;</td><td>160</td><td>n/a<br>n/a</td></tr>
<tr><td><a href="/climate/cdo/about/definitions9and3.shtml#mean9amrh">Mean 9am relative humidity (%) </a></td><td>63</td><td>66</td><td>68</td><td>71</td><td>77</td><td class="highest">80</td><td>79</td><td>73</td><td>67</td><td class="lowest">62</td><td>63</td><td class="lowest">62</td><td>69</td><td>56</td><td>1955<br>2010</td></tr>
<tr><td><a href="/climate/cdo/about/definitions9and3.shtml#mean3pmrh">Mean 3pm relative humidity (%) </a></td><td class="lowest">47</td><td>48</td><td>49</td><td>52</td><td>59</td><td class="highest">63</td><td>61</td><td>56</td><td>53</td><td>50</td><td>49</td><td class="lowest">47</td><td>53</td><td>56</td><td>1955<br>2010</td></tr>
<tr><td><a href="/climate/cdo/about/definitions9and3.shtml#mean9amwind">Mean 9am wind speed (km/h) </a></td><td>10.0</td><td>9.1</td><td>8.9</td><td class="lowest">8.7</td><td>9.1</td><td>9.4</td><td>10.4</td><td>11.3</td><td>12.4</td><td class="highest">12.6</td><td>11.5</td><td>10.8</td><td>10.4</td><td>54</td><td>1955<br>2009</td></tr>
</tbody>
</table>
"""

# Read the table
df = pd.read_html(StringIO(html_table))[0]

# Remove extra columns (Years, Plot, Map, etc.)
df = df.iloc[:, :14]  # Keep only Statistics and months + Annual

# Set column names
df.columns = ['Statistics', 'January', 'February', 'March', 'April', 'May', 'June',
              'July', 'August', 'September', 'October', 'November', 'December', 'Annual']

# Remove Annual column
df = df.drop('Annual', axis=1)

# Create the climate stats array
climate_stats = []

# Define mappings
stat_mappings = {
    'Mean maximum temperature (°C)': ('Temperature', 'Mean_Max_Temp'),
    'Mean minimum temperature (°C)': ('Temperature', 'Mean_Min_Temp'),
    'Mean rainfall (mm)': ('Rainfall', 'Mean_Rainfall'),
    'Decile 5 (median) rainfall (mm)': ('Rainfall', 'Median_Rainfall'),
    'Decile 1 rainfall (mm)': ('Rainfall', 'Decile_1'),
    'Decile 9 rainfall (mm)': ('Rainfall', 'Decile_9'),
    'Mean 9am relative humidity (%)': ('Humidity', 'Mean_9am_RH'),
    'Mean 3pm relative humidity (%)': ('Humidity', 'Mean_3pm_RH'),
    'Mean 9am wind speed (km/h)': ('Wind', 'Mean_9am_Wind'),
}

for idx, row in df.iterrows():
    stat_name = row['Statistics']

    if stat_name in stat_mappings:
        category, metric = stat_mappings[stat_name]

        stat_dict = {
            'Category': category,
            'Metric': metric
        }

        # Add monthly values
        for month in ['January', 'February', 'March', 'April', 'May', 'June',
                     'July', 'August', 'September', 'October', 'November', 'December']:
            value = row[month]
            # Convert to float, handling any non-numeric values
            try:
                stat_dict[month] = float(value)
            except:
                stat_dict[month] = None

        climate_stats.append(stat_dict)

# Save to JSON file
json_dir = Path("melbs/static")
json_dir.mkdir(parents=True, exist_ok=True)
json_file = json_dir / "climate_stats.json"

with open(json_file, 'w') as f:
    json.dump(climate_stats, f, indent=2)

print(f"Climate statistics saved to {json_file}")
print(f"Extracted {len(climate_stats)} statistics")
