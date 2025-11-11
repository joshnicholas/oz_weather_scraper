<script>
    import Chart from '$lib/Chart.svelte';
    import TotalRainChart from '$lib/TotalRainChart.svelte';
    import ClimateChart from '$lib/ClimateChart.svelte';
    import Shapeline from '$lib/Shapeline.svelte';
    import Rainline from '$lib/Rainline.svelte';
    import RainBars from '$lib/RainBars.svelte';

    let { data } = $props();
    let containerWidth = $state(0);
    let tempWidth = $state(0);
    let hourlyRainWidth = $state(0);
    let maxTempWidth = $state(0);
    let totalRainWidth = $state(0);
    let humidityWidth = $state(0);
    let windWidth = $state(0);

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
        </div>

        {#if containerWidth > 0}
        <!-- <nav class="nav">
            <ul>
                <li><a href="#hourly">Hourly</a></li>
                <li><a href="#weekly">Weekly</a></li>
            </ul>
        </nav> -->

        <div class="charts">
            <section id="hourly" class="chart-group">
                <h2 class="section-header">Hourly</h2>
                <div class="chart-section" bind:clientWidth={tempWidth}>
                    <h2>Temperature</h2>
                    <Shapeline
                        data={data.last30}
                        forecastData={data.hourlyForecasts}
                        containerWidth={tempWidth}
                        headline=""
                        subtitle=""
                        chartHeight={150}
                    />
                </div>

                <div class="chart-section" bind:clientWidth={hourlyRainWidth}>
                    <h2>Hourly rainfall</h2>
                    <RainBars
                        data={data.last30}
                        forecastData={data.hourlyForecasts}
                        containerWidth={hourlyRainWidth}
                        headline=""
                        subtitle=""
                        chartHeight={150}
                    />
                </div>
            </section>

            <hr class="section-divider" />

            <section id="weekly" class="chart-group">
                <h2 class="section-header">Weekly</h2>
                <div class="chart-section" bind:clientWidth={maxTempWidth}>
                    <h2>Max temp</h2>
                    <Chart
                        historicData={data.historicTemp}
                        recentData={data.observations.map(d => ({ ...d, Value: d.Temp }))}
                        forecastData={data.forecasts.map(d => ({ ...d, Value: d.Max_temp }))}
                        climateData={data.climate}
                        unit="°C"
                        containerWidth={maxTempWidth}
                        unitColour = {'#7A9AFA'}
                        yMinDefault={0}
                        chartHeight={150}
                    />
                </div>

                <div class="chart-section" bind:clientWidth={totalRainWidth}>
                    <h2>Rain</h2>
                    <TotalRainChart
                        recentData={data.observations.map(d => ({ ...d, Value: d.Rain }))}
                        forecastData={data.forecasts.map(d => ({ ...d, Value: d.Rain }))}
                        climateData={data.climate}
                        unit="mm"
                        containerWidth={totalRainWidth}
                        unitColour = {'#7A9AFA'}
                        yMinDefault={0}
                        chartHeight={150}
                        leftMargin={30}
                    />
                </div>

                <div class="chart-section" bind:clientWidth={humidityWidth}>
                    <h2>Humidity</h2>
                    <ClimateChart
                        observationData={data.observations}
                        subtitle = {""}
                        climateStats={data.climateStats}
                        containerWidth={humidityWidth}
                        unitColour={'#7A9AFA'}
                        unit="%"
                        chartHeight={150}
                        metric9am="Mean_9am_RH"
                        metric3pm="Mean_3pm_RH"
                        dataKey="Humidity"
                    />
                </div>

                <div class="chart-section" bind:clientWidth={windWidth}>
                    <h2>Wind speed</h2>
                    <ClimateChart
                        observationData={data.observations}
                        subtitle = {""}
                        climateStats={data.climateStats}
                        containerWidth={windWidth}
                        unitColour={'#7A9AFA'}
                        unit="km/h"
                        chartHeight={150}
                        metric9am="Mean_9am_Wind"
                        metric3pm="Mean_3pm_Wind"
                        dataKey="Wind"
                        leftMargin={50}
                    />
                </div>
            </section>

        </div>
        {:else}
        <div class="loading-container">
            <p class="loading-text">Loading...</p>
        </div>
        {/if}
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
        padding: 20px 2px;
    }

    @media (min-width: 768px) {
        .dashboard {
            padding: 20px 10px;
        }
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

    .nav {
        text-align: center;
        margin-bottom: 20px;
    }

    .nav ul {
        list-style: none;
        padding: 0;
        margin: 0;
        display: flex;
        justify-content: center;
        gap: 20px;
    }

    .nav li {
        display: inline;
    }

    .nav a {
        color: #000;
        text-decoration: underline;
        font-size: 1.5em;
    }

    .charts {
        display: flex;
        flex-direction: column;
        gap: 40px;
        width: 100%;
    }

    .chart-group {
        display: grid;
        grid-template-columns: 1fr;
        gap: 10px;
        width: 100%;
    }

    @media (min-width: 768px) {
        .chart-group {
            grid-template-columns: 1fr 1fr;
            gap: 5px;
        }
    }

    .chart-section {
        background: transparent;
        border-radius: 8px;
        padding: 0 2px;
        width: 100%;
        box-sizing: border-box;
        overflow: hidden;
    }

    @media (min-width: 768px) {
        .chart-section {
            padding: 5px;
        }
    }

    .section-header {
        grid-column: 1 / -1;
        text-align: center;
        margin-top: 0;
        margin-bottom: 10px;
        color: #000;
        font-weight: bold;
    }

    .section-divider {
        width: 25%;
        margin: 20px auto;
        border: none;
        border-top: 1px solid #000;
    }

    h2 {
        margin-top: 0;
        margin-bottom: 2px;
        color: #000;
        text-align: center;
        font-weight: bold;
    }

    .footer {
        text-align: center;
        font-size: 0.75em;
        color: #000;
        margin-top: 40px;
        padding: 0 2px 20px 2px;
    }

    @media (min-width: 768px) {
        .footer {
            padding: 0 10px 20px 10px;
        }
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

    .loading-text {
        text-align: center;
        font-size: 0.85em;
        color: #000;
        margin: 20px 0;
    }

    .loading-container {
        text-align: center;
        padding: 40px 20px;
    }
</style>
