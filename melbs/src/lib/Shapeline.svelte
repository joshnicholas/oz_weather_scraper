<script>
    import { scaleLinear } from 'd3-scale';
    import { line } from 'd3-shape';
    import { onMount } from 'svelte';

    let { data = [], containerWidth, headline = '', subtitle = '', chartHeight = 300 } = $props();

    let margin = $derived({
        top: 20,
        right: containerWidth < 500 ? 30 : 40,
        bottom: containerWidth < 500 ? 35 : 50,
        left: containerWidth < 500 ? 25 : 25
    });

    let totalHeight = $derived(chartHeight + margin.top + margin.bottom);
    let chartWidth = $derived(containerWidth - margin.left - margin.right);
    let innerWidth = $derived(chartWidth - margin.left - margin.right);
    let innerHeight = $derived(chartHeight);

    // Helper function to get today's date in Melbourne time
    // Initialize with empty string and update on mount to ensure client-side calculation
    let today = $state('');

    onMount(() => {
        // Get date in Melbourne timezone properly
        const formatter = new Intl.DateTimeFormat('en-CA', {
            timeZone: 'Australia/Melbourne',
            year: 'numeric',
            month: '2-digit',
            day: '2-digit'
        });
        today = formatter.format(new Date()); // Format: YYYY-MM-DD
        console.log('Today calculated as:', today);
    });

    // Group data by date
    let dataByDate = $derived.by(() => {
        const grouped = {};
        data.forEach(d => {
            if (!grouped[d.Date]) {
                grouped[d.Date] = [];
            }
            grouped[d.Date].push({
                hour: parseInt(d.Hour),
                temp: parseFloat(d.Temp)
            });
        });

        // Sort each day's data by hour
        Object.keys(grouped).forEach(date => {
            grouped[date].sort((a, b) => a.hour - b.hour);
        });

        return grouped;
    });

    // Get all dates sorted
    let allDates = $derived(Object.keys(dataByDate).sort());

    // Check if each date is today
    let datesWithStatus = $derived(allDates.map(date => ({
        date,
        isToday: date === today
    })));

    // Get min and max temperature across all data
    let minTemp = $derived.by(() => {
        let min = Infinity;
        Object.values(dataByDate).forEach(dayData => {
            dayData.forEach(point => {
                if (point.temp < min) min = point.temp;
            });
        });
        return min !== Infinity ? min : 0;
    });

    let maxTemp = $derived.by(() => {
        let max = 0;
        Object.values(dataByDate).forEach(dayData => {
            dayData.forEach(point => {
                if (point.temp > max) max = point.temp;
            });
        });
        return max > 0 ? max : 30; // Default to 30 if no data
    });

    // Scales
    let xScale = $derived.by(() => {
        return scaleLinear()
            .domain([0, 23]) // 0 to 23 hours (midnight to 11pm)
            .range([0, innerWidth]);
    });

    let yScale = $derived.by(() => {
        return scaleLinear()
            .domain([minTemp, maxTemp])
            .range([innerHeight, 0]); // Inverted for SVG coordinates
    });

    // Line generator
    let lineGenerator = $derived.by(() => {
        return line()
            .x(d => xScale(d.hour))
            .y(d => yScale(d.temp));
    });

    // Generate paths for each date
    let paths = $derived.by(() => {
        return datesWithStatus.map(({ date, isToday }) => ({
            date,
            isToday,
            path: lineGenerator(dataByDate[date]),
            stroke: isToday ? '#000000' : '#7A9AFA',
            opacity: isToday ? 1 : 0.3,
            strokeWidth: 2
        }));
    });

    // Y-axis ticks
    let yTicks = $derived.by(() => {
        const min = minTemp;
        const max = maxTemp;
        const tickCount = 5;
        const step = (max - min) / (tickCount - 1);
        return Array.from({ length: tickCount }, (_, i) => Math.round(min + (i * step)));
    });

    // X-axis ticks (Midnight, 6am, Midday, 6pm, 11pm)
    let xTicks = $derived([0, 6, 12, 18, 23]);

    // Calculate min/max envelope for previous days (not today)
    let previousDaysEnvelope = $derived.by(() => {
        const envelope = {};

        // Get data for all days except today
        Object.entries(dataByDate).forEach(([date, dayData]) => {
            if (date === today) return; // Skip today

            dayData.forEach(point => {
                if (!envelope[point.hour]) {
                    envelope[point.hour] = { min: point.temp, max: point.temp };
                } else {
                    if (point.temp < envelope[point.hour].min) envelope[point.hour].min = point.temp;
                    if (point.temp > envelope[point.hour].max) envelope[point.hour].max = point.temp;
                }
            });
        });

        // Convert to array of points for area path
        const hours = Object.keys(envelope).map(Number).sort((a, b) => a - b);
        const topLine = hours.map(hour => ({ hour, temp: envelope[hour].max }));
        const bottomLine = hours.map(hour => ({ hour, temp: envelope[hour].min })).reverse();

        return [...topLine, ...bottomLine];
    });

    // Get today's latest data point
    let todayLatestPoint = $derived.by(() => {
        const todayData = dataByDate[today];
        if (!todayData || todayData.length === 0) return null;

        // Get the last point (highest hour)
        const lastPoint = todayData[todayData.length - 1];
        return {
            hour: lastPoint.hour,
            temp: lastPoint.temp,
            x: xScale(lastPoint.hour),
            y: yScale(lastPoint.temp)
        };
    });
</script>

<div class="chart-container">
    <h3 class="headline">{headline}</h3>
    {#if subtitle}
        <p class="chart-subtitle">{subtitle}</p>
    {/if}
    <svg width={chartWidth} height={totalHeight}>
        <defs>
            <!-- Diagonal stripe pattern -->
            <pattern id="diagonalStripes" patternUnits="userSpaceOnUse" width="4" height="4" patternTransform="rotate(45)">
                <line x1="0" y1="0" x2="0" y2="4" stroke="#888888" stroke-width="2" />
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
                        x1={xScale(hour)}
                        y1={innerHeight}
                        x2={xScale(hour)}
                        y2={innerHeight + 5}
                        stroke="#333"
                        stroke-width="1"
                    />
                    <text
                        x={xScale(hour)}
                        y={innerHeight + 20}
                        text-anchor="middle"
                        font-size="11"
                        fill="#333"
                    >
                        {hour === 0 ? 'Midnight' : hour === 6 ? '6am' : hour === 12 ? 'Midday' : hour === 18 ? '6pm' : '11pm'}
                    </text>
                </g>
            {/each}

            <!-- Previous days envelope (striped area) -->
            {#if previousDaysEnvelope.length > 0}
                {@const envelopePath = previousDaysEnvelope.map((point, i) =>
                    `${i === 0 ? 'M' : 'L'} ${xScale(point.hour)},${yScale(point.temp)}`
                ).join(' ') + ' Z'}
                <path
                    d={envelopePath}
                    fill="url(#diagonalStripes)"
                    opacity="0.8"
                    stroke="none"
                />
            {/if}

            <!-- Today's line -->
            {#each paths as { date, path, stroke, opacity, strokeWidth, isToday }}
                {#if isToday}
                    <path
                        d={path}
                        fill="none"
                        {stroke}
                        stroke-width={strokeWidth}
                        {opacity}
                        stroke-linecap="round"
                        stroke-linejoin="round"
                    >
                        <title>{date}</title>
                    </path>
                {/if}
            {/each}

            <!-- Latest value label for today -->
            {#if todayLatestPoint}
                <text
                    x={todayLatestPoint.x}
                    y={todayLatestPoint.y - 15}
                    text-anchor="middle"
                    font-size="0.75em"
                    fill="#000"
                    style="filter: drop-shadow(1px 1px 2px rgba(255,255,255,0.8));"
                >
                    {todayLatestPoint.temp.toFixed(1)}°C
                </text>
            {/if}
        </g>
    </svg>
</div>

<style>
    .chart-container {
        margin: 0;
        width: 100%;
        position: relative;
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
    }

    text {
        font-family: Arial, sans-serif;
    }
</style>
