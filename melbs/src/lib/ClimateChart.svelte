<script>
    import { scaleTime, scaleLinear } from 'd3-scale';

    let { observationData = [], climateStats = [], containerWidth, unitColour = '#7A9AFA', recentColour = '#FA9A7A', subtitle = '', unit = '%', chartHeight = 200, metric9am = 'Mean_9am_RH', metric3pm = 'Mean_3pm_RH', dataKey = 'Humidity', leftMargin = 40 } = $props();

    let margin = $derived({
        top: 20,
        right: containerWidth < 500 ? 25 : 10,
        bottom: containerWidth < 500 ? 35 : 50,
        left: containerWidth < 500 ? leftMargin : leftMargin
    });

    let totalHeight = $derived(chartHeight + margin.top + margin.bottom);

    // Tooltip state
    let tooltipVisible = $state(false);
    let tooltipX = $state(0);
    let tooltipY = $state(0);
    let tooltipContent = $state('');

    let chartWidth = $derived(containerWidth - margin.right - margin.left);
    let innerWidth = $derived(chartWidth - margin.left - margin.right);
    let innerHeight = $derived(chartHeight);

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

    // Get current month's mean values for 9am and 3pm metrics
    let monthlyMean9am = $derived(() => {
        const monthNames = ['January', 'February', 'March', 'April', 'May', 'June',
                           'July', 'August', 'September', 'October', 'November', 'December'];
        const currentMonthName = monthNames[currentMonth];

        const statRow = climateStats.find(row =>
            row.Metric === metric9am
        );

        return statRow ? statRow[currentMonthName] : 65;
    });

    let monthlyMean3pm = $derived(() => {
        const monthNames = ['January', 'February', 'March', 'April', 'May', 'June',
                           'July', 'August', 'September', 'October', 'November', 'December'];
        const currentMonthName = monthNames[currentMonth];

        const statRow = climateStats.find(row =>
            row.Metric === metric3pm
        );

        return statRow ? statRow[currentMonthName] : null;
    });

    // Filter observation data for the 7-day range
    let sevenDayData = $derived(() => {
        return sevenDayRange().map(day => {
            const obs = observationData.find(d => d.Date === day.dateString);
            return {
                ...day,
                value: obs?.[dataKey] || null
            };
        }).filter(d => d.value !== null);
    });

    // Scales
    const xScale = (dayIndex) => (dayIndex * innerWidth) / 7 + innerWidth / 14;

    // Y scale - include both mean values and observations
    let yExtent = $derived(() => {
        const values = sevenDayData().map(d => d.value);
        const meanValues = [monthlyMean9am()];
        if (monthlyMean3pm() !== null) {
            meanValues.push(monthlyMean3pm());
        }

        const allValues = [...values, ...meanValues];
        const min = Math.min(...allValues);
        const max = Math.max(...allValues);
        const padding = (max - min) * 0.2; // 20% padding

        return {
            min: min - padding,
            max: max + padding
        };
    });

    const yScale = $derived(() => {
        return scaleLinear()
            .domain([yExtent().min, yExtent().max])
            .range([innerHeight, 0]);
    });

    // Get y positions for the mean lines
    let mean9amY = $derived(yScale()(monthlyMean9am()));
    let mean3pmY = $derived(monthlyMean3pm() !== null ? yScale()(monthlyMean3pm()) : null);

    // Tooltip functions
    function showTooltip(event, point) {
        tooltipVisible = true;
        tooltipX = event.clientX + 10;
        tooltipY = event.clientY - 10;

        const date = new Date(point.dateString);
        const day = date.getDate();
        const month = date.toLocaleDateString('en-AU', { month: 'short' });
        const suffix = getOrdinalSuffix(day);
        const formattedDate = `${day}${suffix} ${month}`;

        tooltipContent = `${Math.round(point.value)}${unit} on ${formattedDate}`;
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

<div class="chart-container">
    {#if subtitle}
        <p class="chart-subtitle">{subtitle}</p>
    {/if}
    <svg width={chartWidth} height={totalHeight} style="background: transparent;">
        <g transform="translate({margin.left}, {margin.top})">

            <!-- Y-axis ticks for both means -->
            <g>
                <line x1="-5" y1={mean9amY} x2="0" y2={mean9amY} stroke="#333"/>
                <text x="-10" y={mean9amY} dy="0.3em" text-anchor="end" font-size="12">{monthlyMean9am().toFixed(0)}{unit}</text>
            </g>
            {#if mean3pmY !== null}
                <g>
                    <line x1="-5" y1={mean3pmY} x2="0" y2={mean3pmY} stroke="#333"/>
                    <text x="-10" y={mean3pmY} dy="0.3em" text-anchor="end" font-size="12">{monthlyMean3pm().toFixed(0)}{unit}</text>
                </g>
            {/if}

            <!-- X-axis labels -->
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
                    {day.date.toLocaleDateString('en-US', { weekday: 'short' })}
                </text>
            {/each}

            {#snippet meanLines()}
                {@const is9amOnTop = mean3pmY !== null ? mean9amY < mean3pmY : true}

                <!-- 9am monthly mean line -->
                <line
                    x1="0"
                    y1={mean9amY}
                    x2={innerWidth}
                    y2={mean9amY}
                    stroke="#000"
                    stroke-width="1"
                    stroke-dasharray="5,5"
                />
                <text
                    x={innerWidth - 5}
                    y={is9amOnTop ? mean9amY - 5 : mean9amY + 12}
                    text-anchor="end"
                    font-size="10"
                    fill="#000"
                >
                    9am average
                </text>

                <!-- 3pm monthly mean line -->
                {#if mean3pmY !== null}
                    <line
                        x1="0"
                        y1={mean3pmY}
                        x2={innerWidth}
                        y2={mean3pmY}
                        stroke="#000"
                        stroke-width="1"
                        stroke-dasharray="5,5"
                    />
                    <text
                        x={innerWidth - 5}
                        y={is9amOnTop ? mean3pmY + 12 : mean3pmY - 5}
                        text-anchor="end"
                        font-size="10"
                        fill="#000"
                    >
                        3pm average
                    </text>
                {/if}
            {/snippet}

            {@render meanLines()}

            <!-- Data points -->
            {#each sevenDayData() as point}
                {@const dayIndex = sevenDayRange().findIndex(d => d.dateString === point.dateString)}
                {#if dayIndex >= 0}
                    {@const dayInfo = sevenDayRange()[dayIndex]}
                    <circle
                        cx={xScale(dayIndex)}
                        cy={yScale()(point.value)}
                        r={containerWidth < 500 ? "5" : "8"}
                        fill={recentColour}
                        stroke="black"
                        stroke-width="1"
                        style="cursor: pointer; filter: drop-shadow(1px 1px 2px rgba(0,0,0,0.3)); outline: none;"
                        onmouseenter={(e) => showTooltip(e, point)}
                        onmouseleave={hideTooltip}
                        ontouchstart={(e) => showTooltip(e.touches[0], point)}
                        ontouchend={hideTooltip}
                    />
                    {#if dayInfo?.isToday}
                        <text
                            x={xScale(dayIndex)}
                            y={yScale()(point.value) - 15}
                            text-anchor="middle"
                            font-size="0.75em"
                            fill="#000"
                        >
                            {Math.round(point.value)}{unit}
                        </text>
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

    .chart-subtitle {
        font-size: 0.8em;
        font-style: italic;
        color: #000;
        margin: 0 0 3px 0;
        text-align: center;
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
