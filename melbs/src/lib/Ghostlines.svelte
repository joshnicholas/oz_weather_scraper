<script>
    import { scaleLinear } from 'd3-scale';
    import { line } from 'd3-shape';

    let { data = [], containerWidth, headline = '', chartHeight = 300 } = $props();

    let margin = $derived({
        top: 40,
        right: 20,
        bottom: 40,
        left: 40
    });

    let totalHeight = $derived(chartHeight + margin.top + margin.bottom);
    let chartWidth = $derived(containerWidth - margin.right - margin.left);
    let innerHeight = $derived(chartHeight);

    // Helper function to get today's date in Melbourne time
    let today = $derived.by(() => {
        const now = new Date();
        const melbDate = new Date(now.toLocaleString('en-US', { timeZone: 'Australia/Melbourne' }));
        return melbDate.toISOString().split('T')[0]; // Format: YYYY-MM-DD
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

    // Get max temperature across all data
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
            .range([0, chartWidth]);
    });

    let yScale = $derived.by(() => {
        return scaleLinear()
            .domain([0, maxTemp])
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
        const max = maxTemp;
        const tickCount = 5;
        const step = max / (tickCount - 1);
        return Array.from({ length: tickCount }, (_, i) => Math.round(i * step));
    });

    // X-axis ticks (every 3 hours)
    let xTicks = $derived([0, 3, 6, 9, 12, 15, 18, 21, 23]);
</script>

<div class="chart-container">
    <h3 class="headline">{headline}</h3>
    <svg width={containerWidth} height={totalHeight}>
        <g transform="translate({margin.left}, {margin.top})">
            <!-- Y-axis ticks and labels -->
            {#each yTicks as tick}
                <g>
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
                    <text
                        x={xScale(hour)}
                        y={innerHeight + 20}
                        text-anchor="middle"
                        font-size="11"
                        fill="#333"
                    >
                        {hour === 0 ? '12am' : hour === 12 ? '12pm' : hour < 12 ? `${hour}am` : `${hour - 12}pm`}
                    </text>
                </g>
            {/each}

            <!-- Data lines -->
            {#each paths as { date, path, stroke, opacity, strokeWidth, isToday }}
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
            {/each}
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

    svg {
        width: 100%;
        display: block;
    }

    text {
        font-family: Arial, sans-serif;
    }
</style>
