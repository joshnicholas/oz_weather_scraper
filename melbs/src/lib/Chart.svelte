<script>
    import { scaleTime, scaleLinear } from 'd3-scale';
    import { interpolateRgb } from 'd3-interpolate';
    import { forceSimulation, forceX, forceY, forceCollide } from 'd3-force';

    let { historicData = [], recentData = [], climateData = [], unit = '', containerWidth, unitColour = '#7A9AFA', recentColour = '#FA9A7A', logarithmic = false, yMinDefault = null, subtitle = '', chartHeight = 200 } = $props();

    let chartContainer;
    let totalHeight = $derived(chartHeight + margin.top + margin.bottom);

    let margin = $derived({
        top: 20,
        right: containerWidth < 500 ? 25 : 10,
        bottom: containerWidth < 500 ? 35 : 50,
        left: containerWidth < 500 ? 25 : 25
    });

    let chartWidth = $derived(containerWidth - margin.right - margin.left)

    // Get current month name
    let currentMonthName = $derived(() => {
        const months = ['January', 'February', 'March', 'April', 'May', 'June',
                       'July', 'August', 'September', 'October', 'November', 'December'];
        return months[today.getMonth()];
    });

    // Tooltip state
    let tooltipVisible = $state(false);
    let tooltipX = $state(0);
    let tooltipY = $state(0);
    let tooltipContent = $state('');

    let innerWidth = $derived(chartWidth - margin.left - margin.right);
    let innerHeight = $derived(chartHeight);

    // Helper function to get date string in Brisbane time
    function getDateString(date) {
        return date.toLocaleDateString('en-AU', {
            timeZone: 'Australia/Brisbane',
            year: 'numeric',
            month: '2-digit',
            day: '2-digit'
        }).split('/').reverse().join('-');
    }

    // Get current date in Brisbane time
    let today = $derived(() => {
        const now = new Date();
        const brisbaneDate = new Date(now.toLocaleString('en-US', { timeZone: 'Australia/Brisbane' }));
        return brisbaneDate;
    });

    let currentMonth = $derived(today().getMonth());
    let currentYear = $derived(today().getFullYear());

    // Get last 3 days before today, today, and next 3 days (7 days total)
    let sevenDayRange = $derived(() => {
        const days = [];
        const date = new Date(today());

        // Last 3 days (not including today, so i goes from 3 to 1)
        for (let i = 3; i >= 1; i--) {
            const targetDate = new Date(date);
            targetDate.setDate(date.getDate() - i);
            days.push({
                date: new Date(targetDate),
                dayNumber: targetDate.getDate(),
                dateString: getDateString(targetDate),
                isPast: true,
                isToday: false
            });
        }

        // Today
        days.push({
            date: new Date(date),
            dayNumber: date.getDate(),
            dateString: getDateString(date),
            isPast: false,
            isToday: true
        });

        // Next 3 days
        for (let i = 1; i <= 3; i++) {
            const targetDate = new Date(date);
            targetDate.setDate(date.getDate() + i);
            days.push({
                date: new Date(targetDate),
                dayNumber: targetDate.getDate(),
                dateString: getDateString(targetDate),
                isPast: false,
                isToday: false,
                isFuture: true
            });
        }

        return days;
    });

    // Process data to add date information
    let processedHistoric = $derived(historicData.map(d => {
        const date = new Date(d.Date);
        return {
            ...d,
            date: date,
            dayNumber: date.getDate(),
            month: date.getMonth(),
            year: date.getFullYear(),
            dateString: d.Date
        };
    }));

    let processedRecent = $derived(recentData.map(d => {
        const date = new Date(d.Date);
        return {
            ...d,
            date: date,
            dayNumber: date.getDate(),
            month: date.getMonth(),
            year: date.getFullYear(),
            dateString: d.Date
        };
    }));

    // Filter historic data for the same day-of-month values as the 7-day range
    let matchingDaysHistoric = $derived(() => {
        const targetDayNumbers = sevenDayRange().map(day => day.dayNumber);
        return processedHistoric.filter(d =>
            targetDayNumbers.includes(d.dayNumber)
        );
    });

    // Color scale based on date
    let allDates = $derived(matchingDaysHistoric().map(d => d.date));

    let timeScale = $derived(() => {
        if (allDates.length === 0) return () => 100;
        const extent = [Math.min(...allDates.map(d => d.getTime())), Math.max(...allDates.map(d => d.getTime()))];
        return scaleTime().domain(extent).range([0, 100]);
    });

    let colourScale = $derived(() => {
        return scaleLinear()
            .domain([0, 100])
            .range(['#FADA7A', unitColour])
            .interpolate(interpolateRgb);
    });

    // Beeswarm simulation
    let beeswarmNodes = $state([]);

    $effect(() => {
        const nodes = matchingDaysHistoric()
            .filter(point => !isNaN(parseFloat(point.Value)))
            .map(point => ({
                ...point,
                targetX: getXForHistoricDay(point.dayNumber),
                targetY: yScale(point.Value),
                x: getXForHistoricDay(point.dayNumber),
                y: yScale(point.Value)
            }))
            .filter(node => node.targetX !== null);

        if (nodes.length === 0) {
            beeswarmNodes = [];
            return;
        }

        const collisionRadius = containerWidth < 500 ? 1.8 : 3.5;
        const simulation = forceSimulation(nodes)
            .force('x', forceX(d => d.targetX).strength(1))
            .force('y', forceY(d => d.targetY).strength(1))
            .force('collide', forceCollide(collisionRadius))
            .stop();

        for (let i = 0; i < 120; i++) {
            simulation.tick();
        }

        // Constrain nodes to not go below the x-axis
        nodes.forEach(node => {
            node.y = Math.min(node.y, innerHeight - 2);
        });

        beeswarmNodes = nodes;
    });

    // Extract monthly average from climate data
    let monthlyAverage = $derived(() => {
        if (!climateData || climateData.length === 0) return null;

        const currentMonth = today().getMonth(); // 0-based (0 = January)
        const monthNames = ['January', 'February', 'March', 'April', 'May', 'June',
                           'July', 'August', 'September', 'October', 'November', 'December'];
        const currentMonthName = monthNames[currentMonth];

        // Look for mean temperature or rainfall data for current month
        let meanRow = null;
        if (unit === '°C') {
            // Look for mean maximum temperature
            meanRow = climateData.find(row =>
                row['Statistic Element'] &&
                row['Statistic Element'].toLowerCase().includes('mean maximum temperature')
            );
        } else if (unit === 'mm') {
            // Look for mean rainfall
            meanRow = climateData.find(row =>
                row['Statistic Element'] &&
                row['Statistic Element'].toLowerCase().includes('mean rainfall')
            );
        }

        if (meanRow && meanRow[currentMonthName]) {
            const value = parseFloat(meanRow[currentMonthName]);
            return isNaN(value) ? null : value;
        }
        return null;
    });

    // Filter recent data for the 7-day range
    let sevenDayRangeRecent = $derived(processedRecent.filter(d =>
        sevenDayRange().some(day => day.dateString === d.dateString)
    ));

    // Scales
    const xScale = (dayIndex) => (dayIndex * innerWidth) / 7 + innerWidth / 14;

    // Function to get x position for a specific date
    const getXForDate = (dateString) => {
        const dayIndex = sevenDayRange().findIndex(day => day.dateString === dateString);
        return dayIndex >= 0 ? xScale(dayIndex) : null;
    };

    // Function to get x position for historic data (based on matching day numbers)
    const getXForHistoricDay = (dayNumber) => {
        const targetDayNumbers = sevenDayRange().map(day => day.dayNumber);
        const dayIndex = targetDayNumbers.indexOf(dayNumber);
        return dayIndex >= 0 ? xScale(dayIndex) : null;
    };

    let allValues = $derived([...processedHistoric, ...processedRecent].map(d => parseFloat(d.Value)).filter(v => !isNaN(v) && (logarithmic ? v > 0 : true)));
    let yMin = $derived(() => {
        if (yMinDefault !== null) return yMinDefault;

        if (allValues.length === 0) return logarithmic ? 0.1 : 0;
        const minValue = Math.min(...allValues);

        if (logarithmic) {
            return Math.max(0.1, minValue * 0.5);
        }

        if (unit === 'mm') {
            // For rainfall, ensure minimum is at least a bit below the lowest value to accommodate beeswarm
            return Math.max(0, minValue - (Math.max(...allValues) * 0.05));
        }
        return minValue;
    });
    let yMax = $derived(Math.max(...allValues) * 1.1 || 100);

    const yScale = (value) => {
        const v = parseFloat(value);
        if (logarithmic) {
            const logMin = Math.log10(yMin());
            const logMax = Math.log10(yMax);
            const logValue = Math.log10(Math.max(0.1, v));
            return innerHeight - ((logValue - logMin) / (logMax - logMin) * innerHeight);
        }
        return innerHeight - ((v - yMin()) / (yMax - yMin()) * innerHeight);
    };

    // Tooltip functions
    function showTooltip(event, point) {
        tooltipVisible = true;
        tooltipX = event.clientX + 10;
        tooltipY = event.clientY - 10;

        const date = new Date(point.Date);
        const day = date.getDate();
        const month = date.toLocaleDateString('en-AU', { month: 'short' });
        const formattedDate = `${day}${getOrdinalSuffix(day)} ${month}`;

        tooltipContent = `${point.Value}${unit} on ${formattedDate}`;
    }

    function hideTooltip() {
        tooltipVisible = false;
    }

    // Function to get ordinal suffix
    function getOrdinalSuffix(day) {
        if (day > 3 && day < 21) return 'th';
        switch (day % 10) {
            case 1: return 'st';
            case 2: return 'nd';
            case 3: return 'rd';
            default: return 'th';
        }
    }
</script>

<div class="chart-container" bind:this={chartContainer}>
    <svg width={chartWidth} height={totalHeight} style="background: transparent;">
        <g transform="translate({margin.left}, {margin.top})">
            <!-- Y-axis ticks and labels -->
            {#each [yMin(), yMin() + (yMax-yMin())/4, yMin() + (yMax-yMin())/2, yMin() + (yMax-yMin())*3/4, yMax] as tick, i}
                <g>
                    <line x1="-5" y1={yScale(tick)} x2="0" y2={yScale(tick)} stroke="#333"/>
                    <text x="-10" y={yScale(tick)} dy="0.3em" text-anchor="end" font-size="12">{tick.toFixed(0)}</text>
                </g>
            {/each}

            <!-- X-axis labels (last 4 days + next 3 days) -->
            {#each sevenDayRange() as day, i}
                <line x1={xScale(i)} y1={innerHeight} x2={xScale(i)} y2={innerHeight + 5} stroke="#333"/>
                <text
                    x={xScale(i)}
                    y={innerHeight + (chartWidth < 500 ? 15 : 20)}
                    text-anchor="middle"
                    font-size={chartWidth < 500 ? "10" : "12"}
                    fill="#000"
                    font-style={day.isFuture ? 'italic' : 'normal'}
                >
                    {`${day.dayNumber}${getOrdinalSuffix(day.dayNumber)}`}
                </text>
            {/each}

            <!-- Monthly average line -->
            {#if monthlyAverage !== null && !isNaN(monthlyAverage)}
                <line
                    x1="0"
                    y1={yScale(monthlyAverage)}
                    x2={innerWidth}
                    y2={yScale(monthlyAverage)}
                    stroke="#ff8c00"
                    stroke-width="2"
                    stroke-dasharray="5,5"
                    opacity="0.8"
                />
                <text
                    x={innerWidth - 5}
                    y={yScale(monthlyAverage) - 5}
                    text-anchor="end"
                    font-size="10"
                    fill="#ff8c00"
                >
                    Monthly avg: {monthlyAverage.toFixed(1)}{unit}
                </text>
            {/if}

            <!-- Historic data points (beeswarm) -->
            {#each beeswarmNodes as node}
                <circle
                    cx={node.x}
                    cy={node.y}
                    r={containerWidth < 500 ? "2" : "4"}
                    fill={colourScale()(timeScale()(node.date))}
                    opacity={0.8}
                />
            {/each}

            <!-- Recent data points for 7-day range (higher opacity, drawn last) -->
            {#each sevenDayRangeRecent as point}
                {#if !isNaN(parseFloat(point.Value))}
                    {#if getXForDate(point.dateString) !== null}
                        {@const dayInfo = sevenDayRange().find(d => d.dateString === point.dateString)}
                        <circle
                            cx={getXForDate(point.dateString)}
                            cy={yScale(point.Value)}
                            r={containerWidth < 500 ? "5" : "10"}
                            fill={recentColour}
                            stroke="black"
                            stroke-width="1"
                            opacity={dayInfo?.isFuture ? "0.5" : "0.8"}
                            style="cursor: pointer; filter: drop-shadow(1px 1px 2px rgba(0,0,0,0.3)); outline: none;"
                            onmouseenter={(e) => showTooltip(e, point)}
                            onmouseleave={hideTooltip}
                            ontouchstart={(e) => showTooltip(e.touches[0], point)}
                            ontouchend={hideTooltip}
                        />
                        {#if dayInfo?.isToday}
                            <text
                                x={getXForDate(point.dateString)}
                                y={yScale(point.Value) - 15}
                                text-anchor="middle"
                                font-size="0.75em"
                                fill="#000"
                                style="filter: drop-shadow(1px 1px 2px rgba(0,0,0,0.3));"
                            >
                                {point.Value}{unit}
                            </text>
                        {/if}
                    {/if}
                {/if}
            {/each}
        </g>
    </svg>

    <!-- Tooltip -->
    {#if tooltipVisible}
        <div
            class="tooltip"
            style="left: {tooltipX}px; top: {tooltipY}px;"
        >
            {tooltipContent}
        </div>
    {/if}
</div>

<style>
    .chart-container {
        margin: 0;
        width: 100%;
        position: relative;
        max-width: 100%;
        overflow: visible;
    }

    svg {
        width: 100%;
        display: block;
    }

    .tooltip {
        position: fixed;
        background: rgba(0, 0, 0, 0.8);
        color: white;
        padding: 8px 12px;
        border-radius: 4px;
        font-size: 12px;
        pointer-events: none;
        z-index: 1000;
        white-space: nowrap;
    }

    text {
        font-family: Arial, sans-serif;
    }
</style>
