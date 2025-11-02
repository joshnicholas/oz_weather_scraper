<script>
    import { scaleLinear } from 'd3-scale';
    import { line } from 'd3-shape';
    import { onMount } from 'svelte';

    let { data = [], forecastData = [], containerWidth, headline = '', subtitle = '', chartHeight = 300 } = $props();

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

            return {
                date: p.date,
                x: xScale(lastPoint.hour),
                y: yScale(lastPoint.temp),
                label: `${day}${getOrdinalSuffix(day)}`,
                opacity: p.opacity * 0.7 // Slightly more transparent than the line
            };
        }).filter(l => l !== null);
    });

    // Process forecast data for today
    let todayForecast = $derived.by(() => {
        if (!forecastData || forecastData.length === 0 || !today) return [];

        // Get the last observed hour for today
        const todayData = dataByDate[today];
        const lastObservedHour = todayData && todayData.length > 0
            ? todayData[todayData.length - 1].hour
            : -1;

        // Filter forecast data for today only, starting at last observed hour
        return forecastData
            .filter(d => d.Date === today && parseInt(d.Hour) >= lastObservedHour)
            .map(d => ({
                hour: parseInt(d.Hour),
                temp: parseFloat(d.Temperature)
            }))
            .sort((a, b) => a.hour - b.hour);
    });

    let forecastPath = $derived.by(() => {
        if (todayForecast.length === 0) return null;
        return lineGenerator(todayForecast);
    });

    // Find max forecast temp and position
    let forecastMaxPoint = $derived.by(() => {
        if (todayForecast.length === 0) return null;

        const maxPoint = todayForecast.reduce((max, point) =>
            point.temp > max.temp ? point : max
        , todayForecast[0]);

        return {
            temp: maxPoint.temp,
            hour: maxPoint.hour,
            x: xScale(maxPoint.hour),
            y: yScale(maxPoint.temp)
        };
    });

    // Find max observed temp for today
    let todayObservedMax = $derived.by(() => {
        if (!today || !dataByDate[today]) return -Infinity;

        const todayData = dataByDate[today];
        if (todayData.length === 0) return -Infinity;

        return Math.max(...todayData.map(d => d.temp));
    });

    // Show forecast max label only if it's higher than observed max and before 3-hour window
    let showForecastMaxLabel = $derived.by(() => {
        // First check: must have forecast max point and it must be higher than observed
        if (!forecastMaxPoint) return false;
        // if (!todayObservedMax || forecastMaxPoint.temp <= todayObservedMax) return false;

        // Must have hour data
        if (typeof forecastMaxPoint.hour !== 'number') return false;

        // Get current hour in Melbourne time
        const now = new Date();
        const formatter = new Intl.DateTimeFormat('en-AU', {
            timeZone: 'Australia/Melbourne',
            hour: 'numeric',
            hour12: false
        });
        const currentHour = parseInt(formatter.format(now));

        // Calculate cutoff: 3 hours before the forecast max hour
        const cutoffHour = forecastMaxPoint.hour - 3;

        // Show label only if current hour is before the cutoff
        // Example: if max is at 14:00 (2pm), cutoff is 11:00 (11am)
        // Show from midnight (0) to 10:59 (hour 10), hide from 11:00 onwards
        return currentHour < cutoffHour;
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
                    {todayLatestPoint.temp.toFixed(1)}°C
                </text>
            {/if}

            <!-- Forecast max label (only if higher than observed and before cutoff) -->
            {#if showForecastMaxLabel && forecastMaxPoint}
                <text
                    x={forecastMaxPoint.x}
                    y={forecastMaxPoint.y - 15}
                    text-anchor="middle"
                    font-size="0.75em"
                    fill="#000"
                    style="filter: drop-shadow(1px 1px 2px rgba(255,255,255,0.8));"
                >
                    {forecastMaxPoint.temp.toFixed(1)}°C
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
</style>
