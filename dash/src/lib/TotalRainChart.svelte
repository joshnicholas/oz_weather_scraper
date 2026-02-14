<script>

    let { recentData = [], forecastData = [], climateData = [], unit = '', containerWidth, unitColour = '#7A9AFA', recentColour = '#FA9A7A', forecastColour = '#FFFFFF', yMinDefault = null, subtitle = '', chartHeight = 200, leftMargin = 25 } = $props();

    let chartContainer;

    let margin = $derived({
        top: 20,
        right: containerWidth < 500 ? 0 : 5,
        bottom: containerWidth < 500 ? 35 : 50,
        left: containerWidth < 500 ? leftMargin : leftMargin
    });

    let totalHeight = $derived(chartHeight + margin.top + margin.bottom);

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

    // Helper function to get date string in Melbourne time
    function getDateString(date) {
        return date.toLocaleDateString('en-AU', {
            timeZone: 'Australia/Melbourne',
            year: 'numeric',
            month: '2-digit',
            day: '2-digit'
        }).split('/').reverse().join('-');
    }

    // Get current date in Melbourne time
    let today = $derived(() => {
        const now = new Date();
        const melbDate = new Date(now.toLocaleString('en-US', { timeZone: 'Australia/Melbourne' }));
        return melbDate;
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

    let processedForecast = $derived(forecastData.map(d => {
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


    // Scales and positioning functions
    let innerWidth = $derived(chartWidth - margin.left - margin.right);
    let innerHeight = $derived(chartHeight);

    const xScale = (dayIndex) => (dayIndex * innerWidth) / 7 + innerWidth / 14;

    // Function to get x position for a specific date
    const getXForDate = (dateString) => {
        const dayIndex = sevenDayRange().findIndex(day => day.dateString === dateString);
        return dayIndex >= 0 ? xScale(dayIndex) : null;
    };

    // Get values only for the 7 days being displayed
    let displayedValues = $derived(() => {
        const targetDays = sevenDayRange().map(day => ({
            dayNumber: day.dayNumber,
            month: day.date.getMonth(),
            dateString: day.dateString
        }));

        const recentValues = processedRecent
            .filter(d => targetDays.some(target => target.dateString === d.dateString))
            .map(d => parseFloat(d.Value));

        const forecastValues = processedForecast
            .filter(d => targetDays.some(target => target.dateString === d.dateString))
            .map(d => parseFloat(d.Value));

        // Include Rain_low and Rain_high for forecast ranges (for mm unit)
        const forecastRangeValues = unit === 'mm' ? processedForecast
            .filter(d => targetDays.some(target => target.dateString === d.dateString))
            .flatMap(d => [parseFloat(d.Rain_low), parseFloat(d.Rain_high)])
            : [];

        return [...recentValues, ...forecastValues, ...forecastRangeValues]
            .filter(v => !isNaN(v));
    });

    let yMin = $derived(() => {
        if (yMinDefault !== null) return yMinDefault;

        if (displayedValues().length === 0) return 0;
        const minValue = Math.min(...displayedValues());

        if (unit === 'mm') {
            // For rainfall, ensure minimum is at least a bit below the lowest value
            return Math.max(0, minValue - (Math.max(...displayedValues()) * 0.05));
        }
        return minValue;
    });
    let yMax = $derived(Math.max(...displayedValues()) * 1.1 || 100);

    const yScale = (value) => {
        const v = parseFloat(value);
        return innerHeight - ((v - yMin()) / (yMax - yMin()) * innerHeight);
    };

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

    // Filter forecast data for the 7-day range
    let sevenDayRangeForecast = $derived(processedForecast.filter(d =>
        sevenDayRange().some(day => day.dateString === d.dateString)
    ));

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
    <div style="text-align: center;">
        <div class="legend">
            <svg width="12" height="12" style="vertical-align: middle;">
                <circle cx="6" cy="6" r="5" fill="#FA9A7A" stroke="black" stroke-width="1" />
            </svg>
            <span>Observed</span>
            <svg width="12" height="12" style="vertical-align: middle; margin-left: 10px;">
                <defs>
                    <pattern id="legendSquareHash" patternUnits="userSpaceOnUse" width="3" height="3">
                        <path d="M-0.5,0.5 l1,-1 M0,3 l3,-3 M2.5,3.5 l1,-1" stroke="white" stroke-width="1"/>
                    </pattern>
                </defs>
                <rect width="12" height="12" fill="url(#legendSquareHash)" stroke="black" stroke-width="1" />
            </svg>
            <span>Forecast</span>
        </div>
    </div>
    <svg width={chartWidth} height={totalHeight} style="background: transparent;">
        <defs>
            <!-- Diagonal hash pattern -->
            <pattern id="diagonalHash" patternUnits="userSpaceOnUse" width="3" height="3">
                <path d="M-0.5,0.5 l1,-1 M0,3 l3,-3 M2.5,3.5 l1,-1" stroke="white" stroke-width="1"/>
            </pattern>
        </defs>
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
                <line x1={xScale(i)} y1={innerHeight + 5} x2={xScale(i)} y2={innerHeight + 10} stroke="#333"/>
                <text
                    x={xScale(i)}
                    y={innerHeight + (chartWidth < 500 ? 20 : 25)}
                    text-anchor="middle"
                    font-size={chartWidth < 500 ? "10" : "12"}
                    fill="#000"
                    font-style={day.isFuture ? 'italic' : 'normal'}
                >
                    {day.date.toLocaleDateString('en-US', { weekday: 'short' })}
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

            <!-- Rain forecast range rectangles (shown behind forecast circles) -->
            {#if unit === 'mm'}
                {#each sevenDayRangeForecast as point}
                    {#if point.Rain_low !== null && point.Rain_low !== undefined && point.Rain_high !== null && point.Rain_high !== undefined && !isNaN(point.Rain_low) && !isNaN(point.Rain_high)}
                        {@const x = getXForDate(point.dateString)}
                        {#if x !== null}
                            {@const rectWidth = innerWidth / 14}
                            {@const rectHeight = Math.abs(yScale(point.Rain_low) - yScale(point.Rain_high))}
                            {@const rectY = Math.min(yScale(point.Rain_low), yScale(point.Rain_high))}
                            <rect
                                x={x - rectWidth/2}
                                y={rectY}
                                width={rectWidth}
                                height={rectHeight}
                                fill="url(#diagonalHash)"
                                opacity="0.6"
                            />
                        {/if}
                    {/if}
                {/each}
            {/if}

            <!-- Forecast data points for 7-day range (circles with diagonal pattern, drawn before observations) -->
            {#each sevenDayRangeForecast as point}
                {#if getXForDate(point.dateString) !== null}
                    {@const x = getXForDate(point.dateString)}
                    {@const lineWidth = innerWidth / 14}
                    {#if !isNaN(parseFloat(point.Value)) && parseFloat(point.Value) > 0}
                        {@const dayInfo = sevenDayRange().find(d => d.dateString === point.dateString)}
                        <circle
                            cx={x}
                            cy={yScale(point.Value)}
                            r={containerWidth < 500 ? "5" : "8"}
                            fill="url(#diagonalHash)"
                            stroke="black"
                            stroke-width="1"
                            opacity={dayInfo?.isToday ? "0.3" : "0.8"}
                            style="cursor: pointer; filter: drop-shadow(1px 1px 2px rgba(0,0,0,0.3)); outline: none;"
                            onmouseenter={(e) => showTooltip(e, point)}
                            onmouseleave={hideTooltip}
                            ontouchstart={(e) => showTooltip(e.touches[0], point)}
                            ontouchend={hideTooltip}
                        />
                    {:else}
                        <line
                            x1={x - lineWidth}
                            y1={innerHeight}
                            x2={x + lineWidth}
                            y2={innerHeight}
                            stroke="#000"
                            stroke-width="1"
                        >
                            <title>Forecast: 0mm on {point.Date}</title>
                        </line>
                    {/if}
                {/if}
            {/each}

            <!-- Recent data points for 7-day range (higher opacity, drawn last to sit on top) -->
            {#each sevenDayRangeRecent as point}
                {#if !isNaN(parseFloat(point.Value))}
                    {#if getXForDate(point.dateString) !== null}
                        {@const dayInfo = sevenDayRange().find(d => d.dateString === point.dateString)}
                        <circle
                            cx={getXForDate(point.dateString)}
                            cy={yScale(point.Value)}
                            r={containerWidth < 500 ? "5" : "8"}
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
                                style="filter: drop-shadow(1px 1px 2px rgba(255,255,255,0.8));"
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
