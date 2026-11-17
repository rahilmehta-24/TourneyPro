// load_tests/scenarios/stress-spike.js
import http from 'k6/http';
import { check, sleep } from 'k6';
import { CONFIG, getApiUrl } from '../config.js';

export const options = {
  stages: [
    { duration: '10s', target: 10 },  // Baseline traffic
    { duration: '15s', target: 100 }, // Sudden spike (e.g. registration launch)
    { duration: '30s', target: 100 }, // Sustained spike
    { duration: '15s', target: 20 },  // Recovery phase
    { duration: '10s', target: 0 },   // Cool down
  ],
  thresholds: {
    // Under extreme spike, allow up to 1.5s p(95) and max 5% error rate
    http_req_duration: ['p(95)<1500'],
    http_req_failed: ['rate<0.05'],
  },
};

export default function () {
  const res = http.get(getApiUrl('/tournaments'), {
    headers: CONFIG.DEFAULT_HEADERS,
    tags: { name: 'GET /api/v1/tournaments (Spike)' },
  });

  check(res, {
    'status is 200': (r) => r.status === 200,
  });

  sleep(Math.random() * 0.5 + 0.2); // Rapid repeated queries during rush
}
