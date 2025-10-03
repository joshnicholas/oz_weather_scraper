<script>
    import Chart from '$lib/Chart.svelte';
    import ClimateChart from '$lib/ClimateChart.svelte';

    let { data } = $props();
    let containerWidth = $state(800);
    let isLogarithmic = $state(true);

    // Get latest observation date and format it
    let latestUpdate = $derived(() => {
        if (!data.lastUpdated) return '';
        const latestDate = new Date(data.lastUpdated);
        const hour = latestDate.getHours();
        const ampm = hour >= 12 ? 'pm' : 'am';
        const displayHour = hour % 12 || 12;
        const day = latestDate.getDate();
        const suffix = day > 3 && day < 21 ? 'th' : ['st', 'nd', 'rd'][day % 10 - 1] || 'th';
        const month = latestDate.toLocaleDateString('en-AU', { month: 'short' });
        return `~${displayHour}${ampm} ${day}${suffix} ${month}`;
    });
</script>

<div class="mx-auto max-w-[800px] min-h-[600px]">
<div class="dashboard" bind:clientWidth={containerWidth}>
        <div class="header">
            <h1>Melb Olympic park</h1>
            <p class="latest-update">Latest data from {latestUpdate()}</p>
        </div>

        <div class="charts">
            <div class="chart-section">
                <h2>Max temp</h2>
                <Chart
                    historicData={data.historicTemp}
                    recentData={data.observations.map(d => ({ ...d, Value: d.Temp }))}
                    climateData={data.climate}
                    unit="°C"
                    {containerWidth}
                    unitColour = {'#7A9AFA'}
                    yMinDefault={0}
                    chartHeight={150}
                />
            </div>

            <hr class="chart-divider" />

            <div class="chart-section">
                <h2>Humidity</h2>
                <ClimateChart
                    observationData={data.observations}
                    subtitle = {"Using 9am relative humidity"}
                    climateStats={data.climateStats}
                    {containerWidth}
                    unitColour={'#7A9AFA'}
                    unit="%"
                    chartHeight={110}
                    metric="Mean_9am_RH"
                    dataKey="Humidity"
                />
            </div>

            <hr class="chart-divider" />

            <div class="chart-section">
                <h2>Wind speed</h2>
                <ClimateChart
                    observationData={data.observations}
                    subtitle = {"Using 9am wind speed"}
                    climateStats={data.climateStats}
                    {containerWidth}
                    unitColour={'#7A9AFA'}
                    unit="km/h"
                    chartHeight={110}
                    metric="Mean_9am_Wind"
                    dataKey="Wind"
                    leftMargin={50}
                />
            </div>

            <hr class="chart-divider" />

            <div class="chart-section">
                <h2>Rainfall</h2>
                <div class="chart-header">
                    <button class="scale-toggle" onclick={() => isLogarithmic = !isLogarithmic}>
                        {isLogarithmic ? 'Logarithmic' : 'Linear'}
                    </button>
                </div>
                <Chart
                    historicData={data.historicRain}
                    recentData={data.observations.map(d => ({ ...d, Value: d.Rain }))}
                    climateData={data.climate}
                    unit="mm"
                    {containerWidth}
                    unitColour = {'#7A9AFA'}
                    logarithmic={isLogarithmic}
                    yMinDefault={isLogarithmic ? 0.1 : 0}
                    chartHeight={175}
                />
            </div>


        </div>
</div>

<div class="footer">
    <p>Data from the <a href="http://www.bom.gov.au/" target="_blank" rel="noopener noreferrer">Australian Bureau of Meteorology</a></p>
    <p>By  <a href="https://joshnicholas.com" target="_blank" rel="noopener noreferrer">Josh</a></p>
</div>
</div>

<style>
    .dashboard {
        max-width: 1200px;
        margin: 0 auto;
        padding: 20px;
    }

    .header {
        text-align: center;
        margin-bottom: 40px;
    }

    h1 {
        color: #333;
        font-weight: bold;
        margin-bottom: 8px;
    }

    .latest-update {
        font-size: 0.8em;
        font-style: italic;
        color: #000;
        margin: 0;
    }

    .charts {
        display: flex;
        flex-direction: column;
        gap: 5px;
        width: 100%;
    }

    .chart-section {
        background: transparent;
        border-radius: 8px;
        padding: 10px;
        width: 100%;
        box-sizing: border-box;
    }

    h2 {
        margin-top: 0;
        margin-bottom: 4px;
        color: #000;
        text-align: center;
        font-weight: bold;
    }

    .chart-header {
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 12px;
        margin-bottom: 10px;
    }

    .scale-toggle {
        font-size: 0.8em;
        color: #000;
        background: transparent;
        border: 1px solid #000;
        border-radius: 4px;
        padding: 4px 12px;
        cursor: pointer;
    }

    .scale-toggle:hover {
        background: rgba(0, 0, 0, 0.05);
    }

    .footer {
        text-align: center;
        font-size: 0.75em;
        color: #000;
        margin-top: 40px;
        padding-bottom: 20px;
    }

    .footer p {
        margin: 8px 0;
    }

    .footer a {
        color: #000;
        text-decoration: underline;
    }

    .footer a:hover {
        opacity: 0.7;
    }

    .chart-divider {
        width: 25%;
        margin: 20px auto;
        border: none;
        border-top: 1px solid #000;
    }
</style>
