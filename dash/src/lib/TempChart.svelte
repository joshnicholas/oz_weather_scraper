<script>
    import { Plot, Line, Dot, Text, AxisX, AxisY } from 'svelteplot';

    let { days = [], averages = [], currentHour = -1 } = $props();

    // Build a lookup: hour → average temp
    let avgByHour = $derived.by(() => {
        const map = {};
        for (const a of averages) {
            map[a.hour] = a.value;
        }
        return map;
    });

    // Separate day categories
    let historicDays = $derived(days.filter(d => d.isHistoric));
    let todayObserved = $derived(days.find(d => d.isToday && d.portion === 'observed'));
    let todayForecast = $derived(days.find(d => d.isToday && d.portion === 'forecast'));
    let futureDays = $derived(days.filter(d => d.isForecast));

    // Historic lines: color based on max temp vs midday average
    let historicLines = $derived.by(() => {
        return historicDays.map(day => ({
            date: day.date,
            data: day.points.map(p => ({ hour: p.hour, value: p.value })),
            stroke: day.maxTemp >= (avgByHour[12] ?? 22) ? '#F8843F' : '#3D45AA',
            opacity: day.opacity
        }));
    });

    let todayObservedData = $derived(
        todayObserved ? todayObserved.points.map(p => ({ hour: p.hour, value: p.value })) : []
    );

    let todayForecastData = $derived(
        todayForecast ? todayForecast.points.map(p => ({ hour: p.hour, value: p.value })) : []
    );

    let futureDayLines = $derived.by(() => {
        return futureDays.map(day => ({
            date: day.date,
            data: day.points.map(p => ({ hour: p.hour, value: p.value }))
        }));
    });

    // Average line data
    let avgLineData = $derived(
        averages.map(a => ({ hour: a.hour, value: a.value }))
    );

    // Current time dot: last point of today's observed data
    let currentDot = $derived.by(() => {
        if (!todayObserved || todayObserved.points.length === 0) return [];
        const last = todayObserved.points[todayObserved.points.length - 1];
        return [{ hour: last.hour, value: last.value }];
    });

    // Max temp for today (across both observed and forecast)
    let todayMaxPoint = $derived.by(() => {
        const allTodayDays = days.filter(d => d.isToday);
        if (allTodayDays.length === 0) return [];

        let maxVal = -Infinity;
        let maxHour = 0;
        for (const day of allTodayDays) {
            for (const p of day.points) {
                if (p.value > maxVal) {
                    maxVal = p.value;
                    maxHour = p.hour;
                }
            }
        }
        if (maxVal === -Infinity) return [];
        return [{ hour: maxHour, value: maxVal, label: `${maxVal.toFixed(1)}\u00B0c` }];
    });

    const xTickFormat = (d) => {
        if (d === 0) return 'Midnight';
        if (d === 6) return '6';
        if (d === 12) return '12';
        if (d === 18) return '6';
        if (d === 23) return '11pm';
        return '';
    };
</script>

<div class="temp-chart">
    <h2>Temperature</h2>
    <div class="legend">
        <svg width="20" height="10" style="vertical-align: middle;">
            <line x1="0" y1="5" x2="20" y2="5" stroke="#000" stroke-width="2" />
        </svg>
        <span>Today</span>
        <svg width="20" height="10" style="vertical-align: middle; margin-left: 8px;">
            <line x1="0" y1="5" x2="20" y2="5" stroke="#000" stroke-width="2" stroke-dasharray="4,3" opacity="0.6" />
        </svg>
        <span>Forecast</span>
    </div>

    <Plot
        x={{ domain: [0, 23] }}
        height={200}
        axes={false}
    >
        <AxisX ticks={[0, 6, 12, 18, 23]} tickFormat={xTickFormat} textAnchor={(d) => d === 0 ? 'start' : d === 23 ? 'end' : 'middle'} title={false} />
        <AxisY title={false} />

        {#if avgLineData.length > 0}
            <Line
                data={avgLineData}
                x="hour"
                y="value"
                stroke="#888"
                strokeDasharray="2,2"
                opacity={0.6}
                strokeWidth={1}
            />
        {/if}

        {#each historicLines as line}
            <Line
                data={line.data}
                x="hour"
                y="value"
                stroke={line.stroke}
                strokeDasharray="4,3"
                opacity={line.opacity}
                strokeWidth={1}
            />
        {/each}

        {#each futureDayLines as line}
            <Line
                data={line.data}
                x="hour"
                y="value"
                stroke="#ccc"
                strokeDasharray="4,3"
                opacity={0.5}
                strokeWidth={1}
            />
        {/each}

        {#if todayForecastData.length > 0}
            <Line
                data={todayForecastData}
                x="hour"
                y="value"
                stroke="#000"
                strokeDasharray="5,4"
                opacity={0.6}
                strokeWidth={2}
            />
        {/if}

        {#if todayObservedData.length > 0}
            <Line
                data={todayObservedData}
                x="hour"
                y="value"
                stroke="#000"
                strokeWidth={2}
            />
        {/if}

        {#if currentDot.length > 0}
            <Dot
                data={currentDot}
                x="hour"
                y="value"
                fill="#000"
                r={3}
            />
        {/if}

        {#if todayMaxPoint.length > 0}
            <Dot
                data={todayMaxPoint}
                x="hour"
                y="value"
                fill="#000"
                r={2}
            />
            <Text
                data={todayMaxPoint}
                x="hour"
                y="value"
                text="label"
                dy={-8}
                fill="#000"
                textAnchor="middle"
            />
        {/if}
    </Plot>
</div>

<style>
    .temp-chart {
        width: 100%;
    }

    h2 {
        text-align: center;
        font-weight: bold;
        margin: 0 0 2px 0;
        color: #000;
    }

    .legend {
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 4px;
        margin-bottom: 5px;
        font-size: 0.5em;
        color: #000;
    }
</style>
