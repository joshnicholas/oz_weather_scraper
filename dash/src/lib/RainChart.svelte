<script>
    import { Plot, BarY, AxisX, AxisY } from 'svelteplot';
    import './chart.css';

    let { days = [], averages = [], probability = [], currentHour = -1, today = '' } = $props();

    // Get today's observed data
    let todayObserved = $derived(days.find(d => d.isToday && d.portion === 'observed'));
    let todayForecast = $derived(days.find(d => d.isToday && d.portion === 'forecast'));

    // Build probability lookup: hour -> probability (0-100)
    let probByHour = $derived.by(() => {
        const map = {};
        if (!probability || !today) return map;
        for (const p of probability) {
            if (p.date === today) {
                map[p.hour] = p.value;
            }
        }
        return map;
    });

    // Map probability to opacity: 0% -> 0.05, 100% -> 0.9
    function probToOpacity(prob) {
        return 0.05 + (prob / 100) * 0.85;
    }

    // Observed bars: solid #3D45AA
    let observedBars = $derived.by(() => {
        if (!todayObserved) return [];
        return todayObserved.points.map(p => ({
            hour: p.hour,
            value: p.value,
        }));
    });

    // Forecast bars: #FFF with opacity from probability
    let forecastBars = $derived.by(() => {
        if (!todayForecast) return [];
        return todayForecast.points
            .filter(p => !todayObserved || p.hour > currentHour)
            .map(p => ({
                hour: p.hour,
                value: p.value,
                opacity: probToOpacity(probByHour[p.hour] ?? 0),
            }));
    });

    // Check if there's any rain at all in today's data
    let hasRain = $derived.by(() => {
        const obsHasRain = observedBars.some(b => b.value > 0);
        const fcstHasRain = forecastBars.some(b => b.value > 0);
        return obsHasRain || fcstHasRain;
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

<div class="chart rain-chart">
    <h2>Precipitation</h2>
    <div class="legend">
        <svg width="12" height="10" style="vertical-align: middle;">
            <rect x="0" y="0" width="12" height="10" fill="#3D45AA" />
        </svg>
        <span>Observed</span>
        <svg width="12" height="10" style="vertical-align: middle; margin-left: 8px;">
            <rect x="0" y="0" width="12" height="10" fill="#FFF" stroke="#ccc" stroke-width="0.5" opacity="0.7" />
        </svg>
        <span>Forecast (opacity = probability)</span>
    </div>

    {#if hasRain}
        <Plot
            x={{ type: 'band', domain: Array.from({ length: 24 }, (_, i) => i) }}
            height={200}
            axes={false}
        >
            <AxisX ticks={[0, 6, 12, 18, 23]} tickFormat={xTickFormat} textAnchor={(d) => d === 0 ? 'start' : d === 23 ? 'end' : 'middle'} title={false} />
            <AxisY title={false} />

            {#if observedBars.length > 0}
                <BarY
                    data={observedBars}
                    x="hour"
                    y="value"
                    fill="#3D45AA"
                />
            {/if}

            {#if forecastBars.length > 0}
                <BarY
                    data={forecastBars}
                    x="hour"
                    y="value"
                    fill="#FFF"
                    stroke="#ddd"
                    strokeWidth={0.5}
                    opacity="opacity"
                />
            {/if}
        </Plot>
    {:else}
        <div class="no-rain">
            <p>No rain</p>
        </div>
    {/if}
</div>

<style>
    .no-rain {
        display: flex;
        align-items: center;
        justify-content: center;
        height: 200px;
    }

    .no-rain p {
        color: #000;
        opacity: 0.8;
        font-variant: tabular-nums;
    }
</style>
