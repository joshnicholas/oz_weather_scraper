import adapter from '@sveltejs/adapter-static';

/** @type {import('@sveltejs/kit').Config} */
const config = {
	kit: {
		adapter: adapter({
			pages: 'build',
			assets: 'build',
			fallback: undefined,
			precompress: true,
			strict: true
		}),
		paths: {
			base: process.env.NODE_ENV === 'production' ? '/oz_weather_scraper' : ''
		}
	}
};

export default config;
