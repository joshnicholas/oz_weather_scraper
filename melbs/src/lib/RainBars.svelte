<script>
    import { scaleLinear, scaleBand } from 'd3-scale';
    import { onMount } from 'svelte';

    let { data = [], forecastData = [], containerWidth, headline = '', subtitle = '', chartHeight = 300 } = $props();

    let margin = $derived({
        top: 20,
        right: containerWidth < 500 ? 80 : 100,
        bottom: containerWidth < 500 ? 35 : 50,
        left: containerWidth < 500 ? 10 : 10
    });

    let totalHeight = $derived(chartHeight + margin.top + margin.bottom);
    let chartWidth = $derived(containerWidth);
    let innerWidth = $derived(containerWidth - margin.left - margin.right);
    let innerHeight = $derived(chartHeight);

    // Helper function to get today's date in Melbourne time
    let today = $state('');

    onMount(() => {
        const formatter = new Intl.DateTimeFormat('en-CA', {
            timeZone: 'Australia/Melbourne',
            year: 'numeric',
            month: '2-digit',
            day: '2-digit'
        });
        today = formatter.format(new Date());
    });

    // Process observation data for today
    let todayObservations = $derived.by(() => {
        if (!data || data.length === 0 || !today) return [];

        return data
            .filter(d => d.Date === today)
            .map(d => ({
                hour: parseInt(d.Hour),
                rain: parseFloat(d.Rain) || 0
            }))
            .sort((a, b) => a.hour - b.hour);
    });

    // Process forecast data for today - only for hours after latest observation
    let todayForecasts = $derived.by(() => {
        if (!forecastData || forecastData.length === 0 || !today) return [];

        // Get the last observed hour from the observations
        const lastObservedHour = todayObservations.length > 0
            ? todayObservations[todayObservations.length - 1].hour
            : -1;

        return forecastData
            .filter(d => d.Date === today && parseInt(d.Hour) > lastObservedHour)
            .map(d => ({
                hour: parseInt(d.Hour),
                rain50: parseFloat(d['Rain - 50%']) || 0,
                rain25: parseFloat(d['Rain - 25%']) || 0,
                rain10: parseFloat(d['Rain - 10%']) || 0
            }))
            .sort((a, b) => a.hour - b.hour);
    });

    // Get max rain value for scale
    let maxRain = $derived.by(() => {
        let max = 0;

        todayObservations.forEach(d => {
            if (d.rain > max) max = d.rain;
        });

        todayForecasts.forEach(d => {
            if (d.rain50 > max) max = d.rain50;
            if (d.rain25 > max) max = d.rain25;
            if (d.rain10 > max) max = d.rain10;
        });

        return max > 0 ? max : 10;
    });

    // Scales
    let xScale = $derived.by(() => {
        return scaleBand()
            .domain(Array.from({ length: 24 }, (_, i) => i))
            .range([0, innerWidth])
            .padding(0.2);
    });

    let yScale = $derived.by(() => {
        return scaleLinear()
            .domain([0, maxRain])
            .range([innerHeight, 0]);
    });

    // Y-axis ticks
    let yTicks = $derived.by(() => {
        const tickCount = 5;
        const step = maxRain / (tickCount - 1);
        return Array.from({ length: tickCount }, (_, i) => Math.round(i * step));
    });

    // X-axis ticks
    let xTicks = $derived([0, 6, 12, 18, 23]);

    let barWidth = $derived(xScale.bandwidth());

    // For grouped bars, divide bandwidth into 3 sections
    let groupBarWidth = $derived(barWidth / 3);
    let groupOffsets = $derived({
        rain50: 0,
        rain25: groupBarWidth,
        rain10: groupBarWidth * 2
    });
</script>

<div class="chart-container">
    <h3 class="headline">{headline}</h3>
    {#if subtitle}
        <p class="chart-subtitle">{subtitle}</p>
    {/if}
    <div style="text-align: center;">
        <div class="legend">
            <span>Likelihood: </span>
            <svg width="12" height="12" style="vertical-align: middle;">
                <defs>
                    <pattern id="legend50" patternUnits="userSpaceOnUse" width="3" height="3">
                        <path d="M-0.5,0.5 l1,-1 M0,3 l3,-3 M2.5,3.5 l1,-1" stroke="#f0f0f0" stroke-width="1"/>
                    </pattern>
                </defs>
                <rect width="12" height="12" fill="url(#legend50)" stroke="#000" stroke-width="1"/>
            </svg>
            <span>50%</span>
            <svg width="12" height="12" style="vertical-align: middle; margin-left: 10px;">
                <defs>
                    <pattern id="legend25" patternUnits="userSpaceOnUse" width="3" height="3">
                        <path d="M-0.5,0.5 l1,-1 M0,3 l3,-3 M2.5,3.5 l1,-1" stroke="#bdbdbd" stroke-width="1"/>
                    </pattern>
                </defs>
                <rect width="12" height="12" fill="url(#legend25)" stroke="#000" stroke-width="1"/>
            </svg>
            <span>25%</span>
            <svg width="12" height="12" style="vertical-align: middle; margin-left: 10px;">
                <defs>
                    <pattern id="legend10" patternUnits="userSpaceOnUse" width="3" height="3">
                        <path d="M-0.5,0.5 l1,-1 M0,3 l3,-3 M2.5,3.5 l1,-1" stroke="#636363" stroke-width="1"/>
                    </pattern>
                </defs>
                <rect width="12" height="12" fill="url(#legend10)" stroke="#000" stroke-width="1"/>
            </svg>
            <span>10%</span>
        </div>
    </div>
    <svg width={chartWidth} height={totalHeight}>
        <defs>
            <!-- Diagonal hash patterns -->
            <pattern id="diagonalHash50" patternUnits="userSpaceOnUse" width="3" height="3">
                <path d="M-0.5,0.5 l1,-1 M0,3 l3,-3 M2.5,3.5 l1,-1" stroke="#f0f0f0" stroke-width="1"/>
            </pattern>
            <pattern id="diagonalHash25" patternUnits="userSpaceOnUse" width="3" height="3">
                <path d="M-0.5,0.5 l1,-1 M0,3 l3,-3 M2.5,3.5 l1,-1" stroke="#bdbdbd" stroke-width="1"/>
            </pattern>
            <pattern id="diagonalHash10" patternUnits="userSpaceOnUse" width="3" height="3">
                <path d="M-0.5,0.5 l1,-1 M0,3 l3,-3 M2.5,3.5 l1,-1" stroke="#636363" stroke-width="1"/>
            </pattern>
        </defs>
        <g transform="translate({margin.left}, {margin.top})">
            <!-- Y-axis ticks and labels -->
            {#each yTicks as tick}
                <g>
                    <line
                        x1="-5"
                        y1={yScale(tick)}
                        x2="0"
                        y2={yScale(tick)}
                        stroke="#333"
                        stroke-width="1"
                    />
                    <text
                        x="-10"
                        y={yScale(tick)}
                        dy="0.32em"
                        text-anchor="end"
                        font-size="12"
                        fill="#333"
                    >
                        {tick}
                    </text>
                </g>
            {/each}

            <!-- X-axis ticks and labels -->
            {#each xTicks as hour}
                <g>
                    <line
                        x1={xScale(hour) + barWidth / 2}
                        y1={innerHeight}
                        x2={xScale(hour) + barWidth / 2}
                        y2={innerHeight + 5}
                        stroke="#333"
                        stroke-width="1"
                    />
                    <text
                        x={xScale(hour) + barWidth / 2}
                        y={innerHeight + 20}
                        text-anchor="middle"
                        font-size="11"
                        fill="#333"
                    >
                        {hour === 0 ? 'Midnight' : hour === 6 ? '6am' : hour === 12 ? 'Midday' : hour === 18 ? '6pm' : '11pm'}
                    </text>
                </g>
            {/each}

            <!-- Observation bars (filled) -->
            {#each todayObservations as obs}
                {#if obs.rain > 0}
                    <rect
                        x={xScale(obs.hour)}
                        y={yScale(obs.rain)}
                        width={barWidth}
                        height={innerHeight - yScale(obs.rain)}
                        fill="#FA9A7A"
                        stroke="#000"
                        stroke-width="1"
                        opacity="0.8"
                    >
                        <title>Observed: {obs.rain}mm at {obs.hour}:00</title>
                    </rect>
                {/if}
            {/each}

            <!-- Forecast bars (patterned fill, grouped) -->
            {#each todayForecasts as forecast}
                <!-- Rain 50% (lightest pattern) -->
                {#if forecast.rain50 > 0}
                    <rect
                        x={xScale(forecast.hour) + groupOffsets.rain50}
                        y={yScale(forecast.rain50)}
                        width={groupBarWidth}
                        height={innerHeight - yScale(forecast.rain50)}
                        fill="url(#diagonalHash50)"
                        stroke="#000"
                        stroke-width="1"
                        opacity="0.8"
                    >
                        <title>50% chance: {forecast.rain50}mm at {forecast.hour}:00</title>
                    </rect>
                {/if}

                <!-- Rain 25% (medium pattern) -->
                {#if forecast.rain25 > 0}
                    <rect
                        x={xScale(forecast.hour) + groupOffsets.rain25}
                        y={yScale(forecast.rain25)}
                        width={groupBarWidth}
                        height={innerHeight - yScale(forecast.rain25)}
                        fill="url(#diagonalHash25)"
                        stroke="#000"
                        stroke-width="1"
                        opacity="0.8"
                    >
                        <title>25% chance: {forecast.rain25}mm at {forecast.hour}:00</title>
                    </rect>
                {/if}

                <!-- Rain 10% (darkest pattern) -->
                {#if forecast.rain10 > 0}
                    <rect
                        x={xScale(forecast.hour) + groupOffsets.rain10}
                        y={yScale(forecast.rain10)}
                        width={groupBarWidth}
                        height={innerHeight - yScale(forecast.rain10)}
                        fill="url(#diagonalHash10)"
                        stroke="#000"
                        stroke-width="1"
                        opacity="0.8"
                    >
                        <title>10% chance: {forecast.rain10}mm at {forecast.hour}:00</title>
                    </rect>
                {/if}
            {/each}
        </g>
    </svg>
</div>

<style>
    .chart-container {
        margin: 0;
        width: 100%;
        position: relative;
        overflow: visible;
    }

    .headline {
        margin: 0 0 10px 0;
        font-size: 1.2em;
        font-weight: 600;
        color: #333;
    }

    .chart-subtitle {
        font-size: 0.8em;
        font-style: italic;
        color: #000;
        margin: 0 0 3px 0;
        text-align: center;
    }

    svg {
        width: 100%;
        display: block;
        overflow: visible;
    }

    text {
        font-family: Arial, sans-serif;
    }

    .legend {
        display: inline-flex;
        justify-content: center;
        align-items: center;
        gap: 5px;
        margin-top: 5px;
        font-size: 0.5em;
        color: #000;
    }
</style>
