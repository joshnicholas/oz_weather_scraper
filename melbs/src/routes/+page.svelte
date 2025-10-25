<script>
    import Chart from '$lib/Chart.svelte';
    import ClimateChart from '$lib/ClimateChart.svelte';
    import Shapeline from '$lib/Shapeline.svelte';

    let { data } = $props();
    let containerWidth = $state(0);
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

<div class="mx-auto max-w-[800px] min-h-[700px]">
<div class="dashboard" bind:clientWidth={containerWidth}>
        <div class="header">
            <h1 style="color:grey">Dashboard currently a bit unstable due to the BOM site redesign</h1>
            <h1>Melbourne Olympic park</h1>
            <p class="latest-update">
                {#if containerWidth > 0 && latestUpdate()}
                    Latest data from {latestUpdate()}
                {:else}
                    &nbsp;
                {/if}
            </p>
            <div class="legend">
                <svg width="12" height="12" style="vertical-align: middle;">
                    <circle cx="6" cy="6" r="4" fill="#7A9AFA" opacity="0.8" />
                </svg>
                <span>Historic data</span>
                <svg width="12" height="12" style="vertical-align: middle; margin-left: 10px;">
                    <circle cx="6" cy="6" r="5" fill="#FA9A7A" stroke="black" stroke-width="1" opacity="0.8" />
                </svg>
                <span>Recent observations</span>
                <svg width="12" height="12" style="vertical-align: middle; margin-left: 10px;">
                    <circle cx="6" cy="6" r="5" fill="#FFFFFF" stroke="black" stroke-width="1" opacity="0.8" />
                </svg>
                <span>Forecasts</span>
                <svg width="12" height="12" style="vertical-align: middle; margin-left: 10px;">
                    <defs>
                        <pattern id="legendStripes" patternUnits="userSpaceOnUse" width="4" height="4" patternTransform="rotate(45)">
                            <line x1="0" y1="0" x2="0" y2="4" stroke="#888888" stroke-width="2" />
                        </pattern>
                    </defs>
                    <rect x="1" y="1" width="10" height="10" fill="url(#legendStripes)" opacity="0.8" />
                </svg>
                <span>Last 30 days</span>
            </div>
        </div>

        <div class="charts">
            {#if containerWidth > 0}
            <div class="chart-section">
                <h2>Max temp</h2>
                <Chart
                    historicData={data.historicTemp}
                    recentData={data.observations.map(d => ({ ...d, Value: d.Temp }))}
                    forecastData={data.forecasts.map(d => ({ ...d, Value: d.Max_temp }))}
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
                <h2>Hourly temps</h2>
                    <Shapeline
                        data={data.last30}
                        {containerWidth}
                        headline=""
                        subtitle="*The shape will look a little weird til 30 days of data has been collected"
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
                    forecastData={data.forecasts.map(d => ({ ...d, Value: d.Rain }))}
                    climateData={data.climate}
                    unit="mm"
                    {containerWidth}
                    unitColour = {'#7A9AFA'}
                    logarithmic={isLogarithmic}
                    yMinDefault={isLogarithmic ? 0.1 : 0}
                    chartHeight={175}
                    leftMargin={30}
                />
            </div>
            {:else}
            <div class="chart-section">
                <p class="loading-text">Loading...</p>
            </div>
            {/if}

        </div>
</div>


</div>
<div class="footer mx-auto max-w-[800px]">
    <p>Data from the <a href="http://www.bom.gov.au/" target="_blank" rel="noopener noreferrer">Australian Bureau of Meteorology</a></p>
    <p>Historic data includes the Melbourne Regional Office</p>

    <p>By  <a href="https://joshnicholas.com" target="_blank" rel="noopener noreferrer">Josh</a></p>
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
        margin-bottom: 2px;
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
        font-size: 0.5em;
        color: #000;
        background: transparent;
        border: 1px solid #000;
        border-radius: 4px;
        padding: 3px 10px;
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

    .legend {
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 5px;
        margin-top: 5px;
        font-size: 0.5em;
        color: #000;
    }

    .loading-text {
        text-align: center;
        font-size: 0.85em;
        color: #000;
        margin: 20px 0;
    }
</style>
