export const prerender = true;

export async function load({ fetch }) {
    try {
        // Fetch the city list and all city data
        const listRes = await fetch('/cities/_list.json');
        const cities = await listRes.json();

        const cityData = {};
        for (const city of cities) {
            const res = await fetch(`/cities/${city}.json`);
            cityData[city] = await res.json();
        }

        // Compute today/currentHour at build time (Melbourne timezone)
        // The page rebuilds hourly so this stays fresh
        const now = new Date();
        const today = new Intl.DateTimeFormat('en-CA', {
            timeZone: 'Australia/Melbourne',
            year: 'numeric',
            month: '2-digit',
            day: '2-digit'
        }).format(now);

        const currentHour = parseInt(new Intl.DateTimeFormat('en-AU', {
            timeZone: 'Australia/Melbourne',
            hour: 'numeric',
            hour12: false
        }).format(now));

        return { cities, cityData, today, currentHour };
    } catch (error) {
        console.error('Error loading data:', error);
        return { cities: [], cityData: {}, today: '', currentHour: -1 };
    }
}
