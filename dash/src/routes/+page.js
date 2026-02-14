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

        return { cities, cityData };
    } catch (error) {
        console.error('Error loading data:', error);
        return { cities: [], cityData: {} };
    }
}
