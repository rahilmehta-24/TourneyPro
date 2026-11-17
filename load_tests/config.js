// load_tests/config.js
export const CONFIG = {
  // Base server configuration
  // TourneyPro run.py defaults to 5001, but can be overridden with __ENV.BASE_URL or __ENV.PORT
  BASE_URL: __ENV.BASE_URL || (__ENV.PORT ? `http://localhost:${__ENV.PORT}` : 'http://localhost:5001'),
  API_PREFIX: '/api/v1',

  // Authentication credentials for load test setup
  AUTH: {
    username: __ENV.AUTH_USERNAME || 'superadmin',
    password: __ENV.AUTH_PASSWORD || 'adminpassword',
  },

  // Default Service Level Objectives (SLOs) / Performance Thresholds
  THRESHOLDS: {
    // 95% of requests must complete below 500ms; 99% below 1s
    http_req_duration: ['p(95)<500', 'p(99)<1000'],
    // HTTP failure rate should be less than 1%
    http_req_failed: ['rate<0.01'],
  },

  // Headers
  DEFAULT_HEADERS: {
    'Accept': 'application/json',
    'User-Agent': 'k6-load-test/1.0 (TourneyPro)',
  },
};

export function getUrl(path) {
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  return `${CONFIG.BASE_URL}${cleanPath}`;
}

export function getApiUrl(endpoint) {
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  return `${CONFIG.BASE_URL}${CONFIG.API_PREFIX}${cleanEndpoint}`;
}
