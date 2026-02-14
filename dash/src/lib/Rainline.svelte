<script>
    import { scaleLinear, scaleLog } from 'd3-scale';
    import { line } from 'd3-shape';
    import { onMount } from 'svelte';

    let { data = [], forecastData = [], containerWidth, headline = '', subtitle = '', chartHeight = 300 } = $props();

    let isLogarithmic = $state(true);

    let margin = $derived({
        top: 20,
        right: containerWidth < 500 ? 100 : 100,
        bottom: containerWidth < 500 ? 35 : 50,
        left: containerWidth < 500 ? 10 : 10
    });

    let totalHeight = $derived(chartHeight + margin.top + margin.bottom);
    let chartWidth = $derived(containerWidth);
    let innerWidth = $derived(containerWidth - margin.left - margin.right);
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

    // Group data by date and make cumulative from midnight
    let dataByDate = $derived.by(() => {
        const grouped = {};
        data.forEach(d => {
            if (!grouped[d.Date]) {
                grouped[d.Date] = [];
            }
            grouped[d.Date].push({
                hour: parseInt(d.Hour),
                rain: parseFloat(d.Rain) || 0
            });
        });

        // Sort each day's data by hour and make cumulative
        Object.keys(grouped).forEach(date => {
            grouped[date].sort((a, b) => a.hour - b.hour);

            // Make rain cumulative from midnight
            let cumulative = 0;
            grouped[date] = grouped[date].map(point => {
                cumulative += point.rain;
                return {
                    hour: point.hour,
                    rain: cumulative
                };
            });
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

    // Get min and max rain across all data
    let minRain = $derived(isLogarithmic ? 0.1 : 0); // Logarithmic needs > 0

    let maxRain = $derived.by(() => {
        let max = 0;
        Object.values(dataByDate).forEach(dayData => {
            dayData.forEach(point => {
                if (point.rain > max) max = point.rain;
            });
        });
        return max > 0 ? max : 10; // Default to 10 if no data
    });

    // Scales
    let xScale = $derived.by(() => {
        return scaleLinear()
            .domain([0, 23]) // 0 to 23 hours (midnight to 11pm)
            .range([0, innerWidth]);
    });

    let yScale = $derived.by(() => {
        if (isLogarithmic) {
            return scaleLog()
                .domain([minRain, maxRain])
                .range([innerHeight, 0]); // Inverted for SVG coordinates
        } else {
            return scaleLinear()
                .domain([minRain, maxRain])
                .range([innerHeight, 0]); // Inverted for SVG coordinates
        }
    });

    // Line generator
    let lineGenerator = $derived.by(() => {
        return line()
            .x(d => xScale(d.hour))
            .y(d => yScale(isLogarithmic && d.rain === 0 ? 0.1 : d.rain));
    });

    // Generate paths for each date
    let paths = $derived.by(() => {
        // Calculate opacity based on date recency
        const sortedDates = allDates.filter(d => d !== today).sort();
        const oldestDate = sortedDates.length > 0 ? new Date(sortedDates[0]) : null;
        const newestDate = sortedDates.length > 0 ? new Date(sortedDates[sortedDates.length - 1]) : null;

        return datesWithStatus.map(({ date, isToday }) => {
            let opacity = 0.3;

            if (!isToday && oldestDate && newestDate) {
                const currentDate = new Date(date);
                const totalRange = newestDate - oldestDate;

                if (totalRange > 0) {
                    // Map from oldest (0.1) to newest (0.9)
                    const position = (currentDate - oldestDate) / totalRange;
                    opacity = 0.1 + (position * 0.7); // 0.1 to 0.9
                } else {
                    // Only one historic date, use high opacity
                    opacity = 0.8;
                }
            } else if (isToday) {
                opacity = 1;
            }

            return {
                date,
                isToday,
                path: lineGenerator(dataByDate[date]),
                stroke: isToday ? '#000' : '#7A9AFA',
                opacity,
                strokeWidth: isToday ? 2 : 1
            };
        });
    });

    // Y-axis ticks
    let yTicks = $derived.by(() => {
        const min = minRain;
        const max = maxRain;
        const tickCount = 5;
        const step = (max - min) / (tickCount - 1);
        return Array.from({ length: tickCount }, (_, i) => Math.round(min + (i * step)));
    });

    // X-axis ticks (Midnight, 6am, Midday, 6pm, 11pm)
    let xTicks = $derived([0, 6, 12, 18, 23]);

    // Get today's latest data point
    let todayLatestPoint = $derived.by(() => {
        const todayData = dataByDate[today];
        if (!todayData || todayData.length === 0) return null;

        // Get the last point (highest hour)
        const lastPoint = todayData[todayData.length - 1];
        // Use 0.1 for logarithmic scale if rain is 0
        const rainValue = isLogarithmic && lastPoint.rain === 0 ? 0.1 : lastPoint.rain;
        return {
            hour: lastPoint.hour,
            rain: lastPoint.rain,
            x: xScale(lastPoint.hour),
            y: yScale(rainValue)
        };
    });

    // Function to get ordinal suffix for day
    function getOrdinalSuffix(day) {
        if (day > 3 && day < 21) return 'th';
        switch (day % 10) {
            case 1: return 'st';
            case 2: return 'nd';
            case 3: return 'rd';
            default: return 'th';
        }
    }

    // Get end point labels for historic lines
    let historicLineLabels = $derived.by(() => {
        return paths.filter(p => !p.isToday).map(p => {
            const dayData = dataByDate[p.date];
            if (!dayData || dayData.length === 0) return null;

            // Get last point of the day
            const lastPoint = dayData[dayData.length - 1];
            const dateObj = new Date(p.date);
            const day = dateObj.getDate();
            // Use 0.1 for logarithmic scale if rain is 0
            const rainValue = isLogarithmic && lastPoint.rain === 0 ? 0.1 : lastPoint.rain;

            return {
                date: p.date,
                x: xScale(lastPoint.hour),
                y: yScale(rainValue),
                label: `${day}${getOrdinalSuffix(day)}`,
                opacity: p.opacity * 0.7 // Slightly more transparent than the line
            };
        }).filter(l => l !== null);
    });

    // Process forecast data for today - use Rain - 50% and make cumulative from observed
    let todayForecast = $derived.by(() => {
        if (!forecastData || forecastData.length === 0 || !today) return [];

        // Get the latest observed cumulative rain for today
        const todayData = dataByDate[today];
        const startingRain = todayData && todayData.length > 0
            ? todayData[todayData.length - 1].rain
            : 0;

        // Filter forecast data for today only
        const filtered = forecastData
            .filter(d => d.Date === today)
            .map(d => ({
                hour: parseInt(d.Hour),
                rain: parseFloat(d['Rain - 50%']) || 0
            }))
            .sort((a, b) => a.hour - b.hour);

        // Make rain cumulative starting from the last observed value
        let cumulative = startingRain;
        return filtered.map(point => {
            cumulative += point.rain;
            return {
                hour: point.hour,
                rain: cumulative
            };
        });
    });

    let forecastPath = $derived.by(() => {
        if (todayForecast.length === 0) return null;
        return lineGenerator(todayForecast);
    });

</script>

<div class="chart-container">
    <h3 class="headline">{headline}</h3>
    {#if subtitle}
        <p class="chart-subtitle">{subtitle}</p>
    {/if}
    <div class="chart-header">
        <button class="scale-toggle" onclick={() => isLogarithmic = !isLogarithmic}>
            {isLogarithmic ? 'Logarithmic' : 'Linear'}
        </button>
    </div>
    <svg width={chartWidth} height={totalHeight}>
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

            <!-- All daily lines (last 30 days) -->
            {#each paths as { date, path, stroke, opacity, strokeWidth, isToday }}
                <path
                    d={path}
                    fill="none"
                    {stroke}
                    stroke-width={strokeWidth}
                    {opacity}
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-dasharray={isToday ? "none" : "4,4"}
                >
                    <title>{date}</title>
                </path>
            {/each}

            <!-- Forecast line for today (black) -->
            {#if forecastPath}
                <path
                    d={forecastPath}
                    fill="none"
                    stroke="black"
                    stroke-width={2}
                    opacity={0.6}
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-dasharray="5,5"
                >
                    <title>Forecast</title>
                </path>
            {/if}

            <!-- Date labels at end of historic lines -->
            {#each historicLineLabels as label}
                <text
                    x={label.x + 5}
                    y={label.y}
                    dy="0.32em"
                    text-anchor="start"
                    font-size="10"
                    fill="#7A9AFA"
                    opacity={label.opacity}
                >
                    {label.label}
                </text>
            {/each}

            <!-- Latest value label for today -->
            {#if todayLatestPoint}
                <circle
                    cx={todayLatestPoint.x}
                    cy={todayLatestPoint.y}
                    r="6"
                    stroke="black"
                    stroke-width="1"
                    fill="#FA9A7A"
                />
                <text
                    x={todayLatestPoint.x}
                    y={todayLatestPoint.y - 15}
                    text-anchor="middle"
                    font-size="0.75em"
                    fill="#000"
                    style="filter: drop-shadow(1px 1px 2px rgba(255,255,255,0.8));"
                >
                    {todayLatestPoint.rain.toFixed(1)}mm
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
        outline: none;
    }

    .scale-toggle:hover {
        background: rgba(0, 0, 0, 0.05);
    }

    .scale-toggle:focus {
        outline: none;
    }

    .scale-toggle:active {
        outline: none;
    }
</style>
