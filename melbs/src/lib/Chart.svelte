<script>
    let { historicData = [], recentData = [], climateData = [], unit = '' } = $props();

    let chartContainer;
    let containerWidth = $state(320);
    let chartHeight = 400;

    // Reactive chart width based on container
    let chartWidth = $derived(Math.max(containerWidth || 800, 320));

    let margin = $derived({
        top: 10,
        right: 10,
        bottom: chartWidth < 500 ? 25 : 30,
        left: 25
    });

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
    let innerHeight = $derived(chartHeight - margin.top - margin.bottom);

    // Get current date and last 7 days of current month
    let today = $derived(new Date());
    let currentMonth = $derived(today.getMonth());
    let currentYear = $derived(today.getFullYear());

    // Get last 4 days and next 3 days (7 days total)
    let sevenDayRange = $derived(() => {
        const days = [];
        const date = new Date(today);

        // Last 4 days (including today as day 0, so i goes from 3 to 0)
        for (let i = 3; i >= 0; i--) {
            const targetDate = new Date(date);
            targetDate.setDate(date.getDate() - i);
            days.push({
                date: new Date(targetDate),
                dayNumber: targetDate.getDate(),
                dateString: targetDate.toISOString().split('T')[0],
                isPast: i > 0,
                isToday: i === 0
            });
        }

        // Next 3 days
        for (let i = 1; i <= 3; i++) {
            const targetDate = new Date(date);
            targetDate.setDate(date.getDate() + i);
            days.push({
                date: new Date(targetDate),
                dayNumber: targetDate.getDate(),
                dateString: targetDate.toISOString().split('T')[0],
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

    // Calculate year-based opacity
    let yearOpacityMap = $derived(() => {
        const years = [...new Set(matchingDaysHistoric().map(d => d.year))].sort();
        const minYear = Math.min(...years);
        const maxYear = Math.max(...years);
        const yearRange = maxYear - minYear;

        const opacityMap = {};
        years.forEach(year => {
            if (yearRange === 0) {
                opacityMap[year] = 1.0;
            } else {
                // Linear interpolation from 0.5 to 1.0
                const progress = (year - minYear) / yearRange;
                opacityMap[year] = 0.5 + (progress * 0.5);
            }
        });
        return opacityMap;
    });

    // Extract monthly average from climate data
    let monthlyAverage = $derived(() => {
        if (!climateData || climateData.length === 0) return null;

        const currentMonth = today.getMonth(); // 0-based (0 = January)
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

    let allValues = $derived([...processedHistoric, ...processedRecent].map(d => parseFloat(d.Value)).filter(v => !isNaN(v)));
    let yMax = $derived(Math.max(...allValues) * 1.1 || 100);
    const yScale = (value) => innerHeight - (parseFloat(value) / yMax * innerHeight);

    // Tooltip functions
    function showTooltip(event, point) {
        tooltipVisible = true;
        tooltipX = event.clientX + 10;
        tooltipY = event.clientY - 10;
        tooltipContent = `${point.Value}${unit} on ${point.Date}`;
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

<div class="chart-container" bind:this={chartContainer} bind:clientWidth={containerWidth}>
    <svg width={chartWidth} height={chartHeight} style="background: transparent;">
        <g transform="translate({margin.left}, {margin.top})">
            <!-- Y-axis -->
            <line x1="0" y1="0" x2="0" y2={innerHeight} stroke="#333" stroke-width="1"/>

            <!-- X-axis -->
            <line x1="0" y1={innerHeight} x2={innerWidth} y2={innerHeight} stroke="#333" stroke-width="1"/>

            <!-- Y-axis unit label -->
            {#if unit}
                <text x="-5" y="-10" text-anchor="start" font-size="10" fill="#666">{unit}</text>
            {/if}

            <!-- Y-axis ticks and labels -->
            {#each [0, yMax/4, yMax/2, (yMax*3)/4, yMax] as tick}
                <g>
                    <line x1="-5" y1={yScale(tick)} x2="0" y2={yScale(tick)} stroke="#333"/>
                    <text x="-10" y={yScale(tick)} dy="0.3em" text-anchor="end" font-size="12">{tick.toFixed(0)}</text>
                </g>
            {/each}

            <!-- X-axis labels (last 4 days + next 3 days) -->
            {#each sevenDayRange() as day, i}
                <text
                    x={xScale(i)}
                    y={innerHeight + (chartWidth < 500 ? 15 : 20)}
                    text-anchor="middle"
                    font-size={chartWidth < 500 ? "10" : "12"}
                    fill={day.isFuture ? '#666' : '#000'}
                    font-style={day.isFuture ? 'italic' : 'normal'}
                >
                    {chartWidth < 500 ? day.dayNumber : `${day.dayNumber}${getOrdinalSuffix(day.dayNumber)}`}
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

            <!-- Historic data points for matching day numbers (year-based opacity) -->
            {#each matchingDaysHistoric() as point}
                {#if !isNaN(parseFloat(point.Value))}
                    {#if getXForHistoricDay(point.dayNumber) !== null}
                        <circle
                            cx={getXForHistoricDay(point.dayNumber)}
                            cy={yScale(point.Value)}
                            r="4"
                            fill="#4299e1"
                            opacity={yearOpacityMap()[point.year] || 0.5}
                        />
                    {/if}
                {/if}
            {/each}

            <!-- Recent data points for 7-day range (higher opacity, drawn last) -->
            {#each sevenDayRangeRecent as point}
                {#if !isNaN(parseFloat(point.Value))}
                    {#if getXForDate(point.dateString) !== null}
                        {@const dayInfo = sevenDayRange().find(d => d.dateString === point.dateString)}
                        <circle
                            cx={getXForDate(point.dateString)}
                            cy={yScale(point.Value)}
                            r="5"
                            fill={dayInfo?.isToday ? "#ff6b35" : dayInfo?.isFuture ? "#888" : "#e53e3e"}
                            opacity={dayInfo?.isFuture ? "0.5" : "0.8"}
                            style="cursor: pointer;"
                            role="button"
                            tabindex="0"
                            aria-label="Data point: {point.Value}{unit} on {point.Date}"
                            onmouseenter={(e) => showTooltip(e, point)}
                            onmouseleave={hideTooltip}
                        />
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
        margin: 20px 0;
        width: 100%;
        position: relative;
        max-width: 100%;
        overflow: hidden;
    }

    svg {
        width: 100%;
        height: auto;
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