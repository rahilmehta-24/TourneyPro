// load_tests/helpers/auth.js
import http from 'k6/http';
import { check } from 'k6';
import { CONFIG, getApiUrl } from '../config.js';

/**
 * Obtains a JWT access token by calling /api/v1/auth/login.
 * Recommended to call this inside the k6 setup() lifecycle hook
 * to prevent hitting the login rate-limiter (10 req/min per IP) during VU load execution.
 */
export function authenticate(username = CONFIG.AUTH.username, password = CONFIG.AUTH.password) {
  const loginUrl = getApiUrl('/auth/login');
  const payload = JSON.stringify({
    username: username,
    password: password,
  });

  const params = {
    headers: {
      'Content-Type': 'application/json',
      ...CONFIG.DEFAULT_HEADERS,
    },
    tags: { name: 'POST /api/v1/auth/login' },
  };

  const res = http.post(loginUrl, payload, params);

  const success = check(res, {
    'login status is 200': (r) => r.status === 200,
    'login returned access_token': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body && body.access_token !== undefined;
      } catch (e) {
        return false;
      }
    },
  });

  if (!success) {
    console.warn(`[WARN] Login failed (Status: ${res.status}). Body: ${res.body}`);
    return null;
  }

  const json = JSON.parse(res.body);
  return json.access_token;
}

/**
 * Generates authorization headers with the given JWT access token.
 */
export function getAuthHeaders(token) {
  return {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`,
    ...CONFIG.DEFAULT_HEADERS,
  };
}
