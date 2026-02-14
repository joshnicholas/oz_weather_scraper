<script>
    import TempChart from '$lib/TempChart.svelte';
    import RainChart from '$lib/RainChart.svelte';
    import CloudChart from '$lib/CloudChart.svelte';
    import HumidityChart from '$lib/HumidityChart.svelte';
    import { onMount } from 'svelte';

    let { data } = $props();
    let selectedCity = $state('Melbourne');

    // Pre-computed at build time in +page.js
    let today = $derived(data.today);
    let currentHour = $derived(data.currentHour);

    // Gate chart rendering on mount — svelteplot needs the DOM for width measurement.
    // This still works for prerendering (onMount fires during prerender) but avoids
    // broken SSR in dev mode where there's no DOM.
    let mounted = $state(false);
    onMount(() => { mounted = true; });

    let cityData = $derived(data.cityData[selectedCity] ?? {});

    // Generic function to process any variable's time series into day objects
    function processDays(entries, todayStr, curHour) {
        if (!todayStr || !entries || entries.length === 0) return [];

        const grouped = {};
        for (const entry of entries) {
            const dt = new Date(entry.time);
            const dateStr = new Intl.DateTimeFormat('en-CA', {
                timeZone: 'Australia/Melbourne',
                year: 'numeric',
                month: '2-digit',
                day: '2-digit'
            }).format(dt);

            const hour = parseInt(new Intl.DateTimeFormat('en-AU', {
                timeZone: 'Australia/Melbourne',
                hour: 'numeric',
                hour12: false
            }).format(dt));

            if (!grouped[dateStr]) grouped[dateStr] = [];
            grouped[dateStr].push({ hour, value: entry.value });
        }

        for (const date of Object.keys(grouped)) {
            grouped[date].sort((a, b) => a.hour - b.hour);
        }

        const allDates = Object.keys(grouped).sort();
        const historicDates = allDates.filter(d => d < todayStr);
        const futureDates = allDates.filter(d => d > todayStr);
        const numHistoric = historicDates.length;

        const result = [];

        historicDates.forEach((date, i) => {
            const points = grouped[date];
            const maxTemp = Math.max(...points.map(p => p.value));
            const opacity = numHistoric > 1
                ? 0.1 + (i / (numHistoric - 1)) * 0.25
                : 0.2;
            result.push({ date, points, maxTemp, opacity, isHistoric: true, isToday: false, isForecast: false, portion: null });
        });

        if (grouped[todayStr]) {
            const todayPoints = grouped[todayStr];
            const maxTemp = Math.max(...todayPoints.map(p => p.value));
            const observed = todayPoints.filter(p => p.hour <= curHour);
            const forecast = todayPoints.filter(p => p.hour >= curHour);

            if (observed.length > 0) {
                result.push({ date: todayStr, points: observed, maxTemp, opacity: 1, isHistoric: false, isToday: true, isForecast: false, portion: 'observed' });
            }
            if (forecast.length > 0) {
                result.push({ date: todayStr, points: forecast, maxTemp, opacity: 0.6, isHistoric: false, isToday: true, isForecast: false, portion: 'forecast' });
            }
        }

        futureDates.forEach(date => {
            const points = grouped[date];
            const maxTemp = Math.max(...points.map(p => p.value));
            result.push({ date, points, maxTemp, opacity: 0.5, isHistoric: false, isToday: false, isForecast: true, portion: null });
        });

        return result;
    }

    // Find the latest observation time (last entry that is in the past)
    let lastUpdated = $derived.by(() => {
        const entries = cityData.temperature_2m;
        if (!entries || entries.length === 0 || !today) return '';
        const now = new Date();
        let latest = null;
        for (const e of entries) {
            const dt = new Date(e.time);
            if (dt <= now) latest = dt;
        }
        if (!latest) return '';
        return new Intl.DateTimeFormat('en-AU', {
            timeZone: 'Australia/Melbourne',
            day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit', hour12: true,
            timeZoneName: 'short'
        }).format(latest);
    });

    let tempDays = $derived(processDays(cityData.temperature_2m, today, currentHour));
    let rainDays = $derived(processDays(cityData.precipitation, today, currentHour));
    let cloudDays = $derived(processDays(cityData.cloud_cover, today, currentHour));
    let humidityDays = $derived(processDays(cityData.relative_humidity_2m, today, currentHour));

    // Process precipitation probability (forecast-only, no historic)
    let precipProbData = $derived.by(() => {
        const entries = cityData.precipitation_probability;
        if (!entries || entries.length === 0 || !today) return [];
        return entries.map(e => {
            const dt = new Date(e.time);
            const dateStr = new Intl.DateTimeFormat('en-CA', {
                timeZone: 'Australia/Melbourne',
                year: 'numeric', month: '2-digit', day: '2-digit'
            }).format(dt);
            const hour = parseInt(new Intl.DateTimeFormat('en-AU', {
                timeZone: 'Australia/Melbourne',
                hour: 'numeric', hour12: false
            }).format(dt));
            return { date: dateStr, hour, value: e.value };
        });
    });
</script>

<div class="mx-auto max-w-[800px] min-h-[700px]">
    <div class="dashboard">
        <div class="header">
            <select class="city-select" bind:value={selectedCity}>
                {#each data.cities as city}
                    <option value={city}>{city}</option>
                {/each}
            </select>
            {#if lastUpdated}
                <p class="last-updated">Last updated {lastUpdated}</p>
            {/if}
        </div>

        {#if mounted}
            <div class="chart-grid">
                <div class="chart-section">
                    <TempChart days={tempDays} averages={cityData.temperature_2m_avg ?? []} {currentHour} />
                </div>
                <div class="mobile-divider"><hr /></div>
                <div class="chart-section">
                    <RainChart days={rainDays} averages={cityData.precipitation_avg ?? []} probability={precipProbData} {currentHour} {today} />
                </div>
            </div>
            <div class="mobile-divider between-grids"><hr /></div>
            <div class="chart-grid">
                <div class="chart-section">
                    <CloudChart days={cloudDays} {currentHour} />
                </div>
                <div class="mobile-divider"><hr /></div>
                <div class="chart-section">
                    <HumidityChart days={humidityDays} averages={cityData.relative_humidity_2m_avg ?? []} {currentHour} />
                </div>
            </div>
        {/if}
    </div>
</div>

<div class="footer mx-auto max-w-[800px]">
    <p>Data from the <a href="http://www.bom.gov.au/" target="_blank" rel="noopener noreferrer">Australian Bureau of Meteorology</a> via <a href='https://open-meteo.com/'>Open Meteo</a></p>
    <!-- <p>Historic data includes the Melbourne Regional Office</p> -->
    <p>By <a href="https://joshnicholas.com" target="_blank" rel="noopener noreferrer">Josh</a></p>
</div>

<style>
    .dashboard {
        max-width: 800px;
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

    .last-updated {
        margin: 6px 0 0 0;
        font-size: 11px;
        color: #000;
        opacity: 0.8;
        font-variant: tabular-nums;
    }

    .city-select {
        background: transparent;
        background-color: transparent;
        border: none;
        border-radius: 0;
        outline: none;
        color: #333;
        font-weight: bold;
        font-size: inherit;
        font-family: inherit;
        cursor: pointer;
        appearance: none;
        -webkit-appearance: none;
        -moz-appearance: none;
        padding: 0 16px 0 0;
        text-align: center;
        background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6'%3E%3Cpath d='M0 0l5 6 5-6z' fill='%23333'/%3E%3C/svg%3E");
        background-repeat: no-repeat;
        background-position: right center;
        background-size: 10px 6px;
    }

    .city-select option {
        background: #fff;
        color: #333;
    }

    .chart-grid {
        display: grid;
        grid-template-columns: 1fr;
        gap: 10px;
        width: 100%;
        position: relative;
    }

    .mobile-divider {
        display: flex;
        justify-content: center;
        padding: 0;
    }

    .mobile-divider hr {
        border: none;
        height: 1px;
        width: 50%;
        background: #000;
        margin: 0;
    }

    .mobile-divider.between-grids {
        padding: 10px 0;
    }

    @media (min-width: 768px) {
        .mobile-divider {
            display: none;
        }

        .chart-grid {
            grid-template-columns: 1fr 1fr;
            gap: 5px;
        }

        /* Vertical divider between columns */
        .chart-grid::after {
            content: '';
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            width: 1px;
            height: 50%;
            background: #000;
        }
    }

    .chart-section {
        background: transparent;
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

    .footer {
        text-align: center;
        font-size: 0.75em;
        color: #000;
        margin-top: 20px;
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

</style>
