// load_tests/scenarios/authenticated-user.js
import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Trend } from 'k6/metrics';
import { CONFIG, getApiUrl } from '../config.js';
import { authenticate, getAuthHeaders } from '../helpers/auth.js';

const meDuration = new Trend('auth_users_me_duration');
const notificationsDuration = new Trend('auth_notifications_duration');

export const options = {
  stages: [
    { duration: '15s', target: 5 },  // Warm-up to 5 VUs
    { duration: '30s', target: 20 }, // Normal load: 20 VUs
    { duration: '30s', target: 40 }, // Peak load: 40 VUs
    { duration: '15s', target: 0 },  // Ramp down to 0
  ],
  thresholds: {
    ...CONFIG.THRESHOLDS,
    auth_users_me_duration: ['p(95)<400'],
    auth_notifications_duration: ['p(95)<400'],
  },
};

export function setup() {
  console.log(`[SETUP] Authenticating with ${CONFIG.BASE_URL} as ${CONFIG.AUTH.username}`);
  const token = authenticate();
  if (!token) {
    throw new Error('Authentication failed in setup. Ensure server is running and credentials are valid.');
  }
  return { token };
}

export default function (data) {
  const headers = getAuthHeaders(data.token);

  group('1. Profile & Session Validation', function () {
    const res = http.get(getApiUrl('/users/me'), {
      headers: headers,
      tags: { name: 'GET /api/v1/users/me' },
    });
    meDuration.add(res.timings.duration);

    check(res, {
      'users/me status 200': (r) => r.status === 200,
    });
  });

  sleep(Math.random() * 1.5 + 0.5);

  group('2. User Notifications & Preferences', function () {
    const notifRes = http.get(getApiUrl('/notifications'), {
      headers: headers,
      tags: { name: 'GET /api/v1/notifications' },
    });
    notificationsDuration.add(notifRes.timings.duration);

    check(notifRes, {
      'notifications status 200': (r) => r.status === 200,
    });

    const prefRes = http.get(getApiUrl('/users/notification-preferences'), {
      headers: headers,
      tags: { name: 'GET /api/v1/users/notification-preferences' },
    });
    check(prefRes, {
      'notification-preferences status 200': (r) => r.status === 200,
    });
  });

  sleep(Math.random() * 1.5 + 0.5);

  group('3. My Registrations & Academy Membership', function () {
    const regRes = http.get(getApiUrl('/users/my-registrations'), {
      headers: headers,
      tags: { name: 'GET /api/v1/users/my-registrations' },
    });
    check(regRes, {
      'my-registrations status 200': (r) => r.status === 200,
    });

    const acadRes = http.get(getApiUrl('/academies/my-application'), {
      headers: headers,
      tags: { name: 'GET /api/v1/academies/my-application' },
    });
    check(acadRes, {
      'my-application status 200 or 404': (r) => r.status === 200 || r.status === 404,
    });
  });

  sleep(Math.random() * 2 + 1);
}
