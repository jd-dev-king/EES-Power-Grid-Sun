window.POWER_GRID_SUN_CONFIG = {
  apiBaseUrl:
    localStorage.getItem('eesApiBase') ||
    'https://ees-power-grid-sun-production.up.railway.app',

  // For local/demo use only. Do not place a production secret in a public GitHub Pages build.
  apiKey: localStorage.getItem('eesPowerGridApiKey') || 'change-me',

  refreshMs: 5000,
};