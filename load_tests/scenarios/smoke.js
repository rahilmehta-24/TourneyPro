// load_tests/scenarios/smoke.js
import http from 'k6/http';
import { check, sleep } from 'k6';
import { CONFIG, getUrl, getApiUrl } from '../config.js';
import { authenticate, getAuthHeaders } from '../helpers/auth.js';

export const options = {
  vus: 1,
  duration: '10s',
  thresholds: {
    http_req_duration: ['p(95)<1000'], // Smoke test threshold: 95% < 1s
    http_req_failed: ['rate<0.05'],    // Less than 5% failures allowed
  },
};

export function setup() {
  console.log(`[SETUP] Starting smoke test against ${CONFIG.BASE_URL}`);
  const token = authenticate();
  return { token };
}

export default function (data) {
  // 1. Web Home Page
  {
    const res = http.get(getUrl('/'), { tags: { name: 'GET / (Home)' } });
    check(res, {
      'home page status is 200': (r) => r.status === 200,
    });
  }
  sleep(0.5);

  // 2. Public API - Tournaments List
  {
    const res = http.get(getApiUrl('/tournaments'), {
      headers: CONFIG.DEFAULT_HEADERS,
      tags: { name: 'GET /api/v1/tournaments' },
    });
    check(res, {
      'tournaments status is 200': (r) => r.status === 200,
    });
  }
  sleep(0.5);

  // 3. Public API - Academies List
  {
    const res = http.get(getApiUrl('/academies'), {
      headers: CONFIG.DEFAULT_HEADERS,
      tags: { name: 'GET /api/v1/academies' },
    });
    check(res, {
      'academies status is 200': (r) => r.status === 200,
    });
  }
  sleep(0.5);

  // 4. Public API - Leaderboard
  {
    const res = http.get(getApiUrl('/leaderboard'), {
      headers: CONFIG.DEFAULT_HEADERS,
      tags: { name: 'GET /api/v1/leaderboard' },
    });
    check(res, {
      'leaderboard status is 200': (r) => r.status === 200,
    });
  }
  sleep(0.5);

  // 5. Authenticated API - Current User (/users/me)
  if (data.token) {
    const authHeaders = getAuthHeaders(data.token);
    const res = http.get(getApiUrl('/users/me'), {
      headers: authHeaders,
      tags: { name: 'GET /api/v1/users/me' },
    });
    check(res, {
      'authenticated /users/me status is 200': (r) => r.status === 200,
      'user payload contains id': (r) => {
        try {
          const body = JSON.parse(r.body);
          return body.user && body.user.id !== undefined;
        } catch (e) {
          return false;
        }
      },
    });
  }
  sleep(0.5);
}

export function teardown() {
  console.log('[TEARDOWN] Smoke test completed.');
}
