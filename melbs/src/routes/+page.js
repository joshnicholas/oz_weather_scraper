export async function load({ fetch }) {
    try {
        // Load historic data
        const historicTempResponse = await fetch('/historic_temp.json');
        const historicRainResponse = await fetch('/historic_rain.json');

        // Load recent observations
        const observationsResponse = await fetch('/observations.json');

        // Load climate data
        const climateResponse = await fetch('/climate.json');

        // Load last updated timestamp
        const lastUpdatedResponse = await fetch('/last_updated.json');

        // Load climate statistics
        const climateStatsResponse = await fetch('/climate_stats.json');

        const historicTemp = await historicTempResponse.json();
        const historicRain = await historicRainResponse.json();
        const observations = await observationsResponse.json();
        const climate = await climateResponse.json();
        const lastUpdated = await lastUpdatedResponse.json();
        const climateStats = await climateStatsResponse.json();

        return {
            historicTemp,
            historicRain,
            observations,
            climate,
            lastUpdated: lastUpdated.lastUpdated,
            climateStats
        };
    } catch (error) {
        console.error('Error loading data:', error);
        return {
            historicTemp: [],
            historicRain: [],
            observations: [],
            climate: [],
            lastUpdated: null,
            climateStats: []
        };
    }
}
