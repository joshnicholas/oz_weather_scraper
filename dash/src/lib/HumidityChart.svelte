<script>
    import { Plot, Line, Dot, AxisX, AxisY } from 'svelteplot';

    let { days = [], averages = [], currentHour = -1 } = $props();

    let avgByHour = $derived.by(() => {
        const map = {};
        for (const a of averages) map[a.hour] = a.value;
        return map;
    });

    let historicDays = $derived(days.filter(d => d.isHistoric));
    let todayObserved = $derived(days.find(d => d.isToday && d.portion === 'observed'));
    let todayForecast = $derived(days.find(d => d.isToday && d.portion === 'forecast'));
    let futureDays = $derived(days.filter(d => d.isForecast));

    // Compute the average of all daily maxes to use as reference
    let avgDailyMax = $derived.by(() => {
        if (averages.length === 0) return 50;
        return Math.max(...averages.map(a => a.value));
    });

    // Historic lines: all #ccc, opacity based on distance from average daily max
    // Closer to average = more opaque, further = less opaque
    let historicLines = $derived.by(() => {
        if (historicDays.length === 0) return [];

        // Collect all daily max values to find the range of distances
        const distances = historicDays.map(day => Math.abs(day.maxTemp - avgDailyMax));
        const maxDistance = Math.max(...distances, 1);

        return historicDays.map(day => {
            const distance = Math.abs(day.maxTemp - avgDailyMax);
            // Close to average → high opacity (0.5), far from average → low opacity (0.05)
            const opacity = 0.5 - (distance / maxDistance) * 0.45;
            return {
                date: day.date,
                data: day.points.map(p => ({ hour: p.hour, value: p.value })),
                opacity
            };
        });
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

    let avgLineData = $derived(
        averages.map(a => ({ hour: a.hour, value: a.value }))
    );

    let currentDot = $derived.by(() => {
        if (!todayObserved || todayObserved.points.length === 0) return [];
        const last = todayObserved.points[todayObserved.points.length - 1];
        return [{ hour: last.hour, value: last.value }];
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

<div class="humidity-chart">
    <h2>Humidity</h2>
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
                stroke="#F8843F"
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
                opacity={0.3}
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
    </Plot>
</div>

<style>
    .humidity-chart {
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
