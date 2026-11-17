// load_tests/scenarios/combined-load.js
import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { CONFIG, getApiUrl } from '../config.js';
import { authenticate, getAuthHeaders } from '../helpers/auth.js';

export const options = {
  scenarios: {
    // 70% of traffic: Anonymous / public visitors browsing tournaments & leaderboards
    public_visitors: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '30s', target: 20 },
        { duration: '1m', target: 50 },
        { duration: '30s', target: 0 },
      ],
      exec: 'publicFlow',
    },

    // 30% of traffic: Logged-in players checking profiles, registrations, notifications
    authenticated_players: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '30s', target: 10 },
        { duration: '1m', target: 20 },
        { duration: '30s', target: 0 },
      ],
      exec: 'authenticatedFlow',
    },
  },
  thresholds: CONFIG.THRESHOLDS,
};

export function setup() {
  console.log(`[SETUP] Initializing combined load test on ${CONFIG.BASE_URL}`);
  const token = authenticate();
  return { token };
}

// Public browsing flow
export function publicFlow() {
  group('Public: Tournaments', function () {
    const res = http.get(getApiUrl('/tournaments'), {
      headers: CONFIG.DEFAULT_HEADERS,
      tags: { name: 'GET /api/v1/tournaments' },
    });
    check(res, { 'tournaments status 200': (r) => r.status === 200 });
  });

  sleep(Math.random() * 1.5 + 0.5);

  group('Public: Leaderboard & Academies', function () {
    const lbRes = http.get(getApiUrl('/leaderboard'), {
      headers: CONFIG.DEFAULT_HEADERS,
      tags: { name: 'GET /api/v1/leaderboard' },
    });
    check(lbRes, { 'leaderboard status 200': (r) => r.status === 200 });

    const acadRes = http.get(getApiUrl('/academies'), {
      headers: CONFIG.DEFAULT_HEADERS,
      tags: { name: 'GET /api/v1/academies' },
    });
    check(acadRes, { 'academies status 200': (r) => r.status === 200 });
  });

  sleep(Math.random() * 2 + 1);
}

// Authenticated player flow
export function authenticatedFlow(data) {
  if (!data.token) {
    sleep(1);
    return;
  }

  const headers = getAuthHeaders(data.token);

  group('Auth: Profile & Notifications', function () {
    const meRes = http.get(getApiUrl('/users/me'), {
      headers: headers,
      tags: { name: 'GET /api/v1/users/me' },
    });
    check(meRes, { 'users/me status 200': (r) => r.status === 200 });

    const notifRes = http.get(getApiUrl('/notifications'), {
      headers: headers,
      tags: { name: 'GET /api/v1/notifications' },
    });
    check(notifRes, { 'notifications status 200': (r) => r.status === 200 });
  });

  sleep(Math.random() * 1.5 + 0.5);

  group('Auth: Registrations', function () {
    const regRes = http.get(getApiUrl('/users/my-registrations'), {
      headers: headers,
      tags: { name: 'GET /api/v1/users/my-registrations' },
    });
    check(regRes, { 'my-registrations status 200': (r) => r.status === 200 });
  });

  sleep(Math.random() * 2 + 1);
}
