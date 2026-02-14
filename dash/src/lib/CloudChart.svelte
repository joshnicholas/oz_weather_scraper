<script>
    import { Plot, AreaY, AxisX, AxisY } from 'svelteplot';
    import './chart.css';

    let { days = [], currentHour = -1 } = $props();

    let todayObserved = $derived(days.find(d => d.isToday && d.portion === 'observed'));
    let todayForecast = $derived(days.find(d => d.isToday && d.portion === 'forecast'));

    // Combine today's full data for the area fill
    let todayAllData = $derived.by(() => {
        const allToday = days.filter(d => d.isToday);
        if (allToday.length === 0) return [];
        const byHour = {};
        for (const day of allToday) {
            for (const p of day.points) {
                if (day.portion === 'observed' || !(p.hour in byHour)) {
                    byHour[p.hour] = p.value;
                }
            }
        }
        return Object.entries(byHour)
            .map(([h, v]) => ({ hour: Number(h), value: v }))
            .sort((a, b) => a.hour - b.hour);
    });

    // Forecast-only portion of today (for hash overlay)
    let todayForecastData = $derived.by(() => {
        if (!todayForecast) return [];
        return todayForecast.points
            .filter(p => !todayObserved || p.hour > currentHour)
            .map(p => ({ hour: p.hour, value: p.value }));
    });

    // Future forecast days combined
    let futureDays = $derived(days.filter(d => d.isForecast));
    let futureDayLines = $derived.by(() => {
        return futureDays.map(day => ({
            date: day.date,
            data: day.points.map(p => ({ hour: p.hour, value: p.value }))
        }));
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

<!-- Hidden SVG for pattern definition (document-global) -->
<svg width="0" height="0" style="position: absolute;">
    <defs>
        <pattern id="cloud-hash" width="4" height="4" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
            <line x1="0" y1="0" x2="0" y2="4" stroke="#FFF" stroke-width="1.5" />
        </pattern>
    </defs>
</svg>

<div class="chart cloud-chart">
    <h2>Cloud cover</h2>
    <div class="legend">
        <svg width="20" height="10" style="vertical-align: middle;">
            <rect x="0" y="0" width="20" height="10" fill="#435663" opacity="0.7" />
        </svg>
        <span>Observed</span>
        <svg width="20" height="10" style="vertical-align: middle; margin-left: 8px;">
            <rect x="0" y="0" width="20" height="10" fill="#435663" opacity="0.7" />
            <rect x="0" y="0" width="20" height="10" fill="url(#cloud-hash)" />
        </svg>
        <span>Forecast</span>
    </div>

    <Plot
        x={{ domain: [0, 23] }}
        y={{ domain: [0, 100] }}
        height={200}
        axes={false}
    >
        <AxisX ticks={[0, 6, 12, 18, 23]} tickFormat={xTickFormat} textAnchor={(d) => d === 0 ? 'start' : d === 23 ? 'end' : 'middle'} title={false} />
        <AxisY title={false} />

        {#if todayAllData.length > 0}
            <AreaY
                data={todayAllData}
                x="hour"
                y="value"
                fill="#435663"
                fillOpacity={0.7}
                stroke="#435663"
                strokeWidth={3}
                opacity={1}
            />
        {/if}

        {#if todayForecastData.length > 0}
            <AreaY
                data={todayForecastData}
                x="hour"
                y="value"
                fill="#000"
                class="cloud-forecast-hash"
                stroke="none"
            />
        {/if}

        {#each futureDayLines as line}
            <AreaY
                data={line.data}
                x="hour"
                y="value"
                fill="#000"
                class="cloud-forecast-hash"
                stroke="none"
            />
        {/each}
    </Plot>
</div>

<style>
    :global(.cloud-forecast-hash path) {
        fill: url(#cloud-hash) !important;
        stroke: none !important;
    }
</style>
