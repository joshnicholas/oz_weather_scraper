<script>
    import Chart from '$lib/Chart.svelte';

    let { data } = $props();
</script>

<div class="dashboard">
    <h1>Melbourne Weather Dashboard</h1>

    <div class="charts">
        <div class="chart-section">
            <h2>Temperature</h2>
            <Chart
                historicData={data.historicTemp}
                recentData={data.observations.map(d => ({ ...d, Value: d.Temp }))}
                climateData={data.climate}
                unit="°C"
            />
        </div>

        <div class="chart-section">
            <h2>Rainfall</h2>
            <Chart
                historicData={data.historicRain}
                recentData={data.observations.map(d => ({ ...d, Value: d.Rain }))}
                climateData={data.climate}
                unit="mm"
            />
        </div>
    </div>
</div>

<style>
    .dashboard {
        max-width: 1200px;
        margin: 0 auto;
        padding: 20px;
    }

    h1 {
        text-align: center;
        color: #333;
        margin-bottom: 40px;
    }

    .charts {
        display: flex;
        flex-direction: column;
        gap: 10px;
        width: 100%;
    }

    .chart-section {
        background: transparent;
        border-radius: 8px;
        padding: 20px;
        width: 100%;
        box-sizing: border-box;
    }

    h2 {
        margin-top: 0;
        color: #555;
        padding-bottom: 10px;
    }
</style>
