// load_tests/scenarios/production-load.js
import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Trend } from 'k6/metrics';
import { CONFIG, getUrl, getApiUrl } from '../config.js';
import { authenticate, getAuthHeaders } from '../helpers/auth.js';

const tournamentsDuration = new Trend('prod_tournaments_duration');
const leaderboardDuration = new Trend('prod_leaderboard_duration');
const homeDuration = new Trend('prod_home_duration');

export const options = {
  stages: [
    { duration: '15s', target: 5 },  // Warm-up serverless instances (5 VUs)
    { duration: '30s', target: 15 }, // Normal concurrent production traffic (15 VUs)
    { duration: '30s', target: 25 }, // Peak production traffic (25 VUs)
    { duration: '15s', target: 0 },  // Cool down
  ],
  thresholds: {
    http_req_duration: ['p(95)<2500'], // 95% of serverless requests under 2.5s
    http_req_failed: ['rate<0.02'],    // Error rate under 2%
    prod_tournaments_duration: ['p(95)<2000'],
  },
};

export function setup() {
  console.log(`[SETUP] Initializing production load test against ${CONFIG.BASE_URL}`);
  const token = authenticate();
  return { token };
}

export default function (data) {
  const authHeaders = data && data.token ? getAuthHeaders(data.token) : CONFIG.DEFAULT_HEADERS;

  // 1. Home page (Edge CDN)
  group('1. Web Home Page', function () {
    const res = http.get(getUrl('/'), {
      headers: CONFIG.DEFAULT_HEADERS,
      tags: { name: 'GET / (Home)' },
    });
    homeDuration.add(res.timings.duration);

    check(res, {
      'home status 200': (r) => r.status === 200,
    });
  });

  sleep(Math.random() * 1.5 + 0.5); // Human think time: 0.5s - 2.0s

  // 2. Public API - Tournaments List & Details
  group('2. Public Tournaments', function () {
    const res = http.get(getApiUrl('/tournaments'), {
      headers: CONFIG.DEFAULT_HEADERS,
      tags: { name: 'GET /api/v1/tournaments' },
    });
    tournamentsDuration.add(res.timings.duration);

    check(res, {
      'tournaments status 200': (r) => r.status === 200,
      'tournaments count >= 0': (r) => {
        try {
          const body = JSON.parse(r.body);
          return body.success === true && body.count !== undefined;
        } catch (e) {
          return false;
        }
      },
    });

    // Dynamic slug lookup
    let slug = 'the-blossom-cup';
    try {
      const body = JSON.parse(res.body);
      if (body.tournaments && body.tournaments.length > 0 && body.tournaments[0].slug) {
        slug = body.tournaments[0].slug;
      }
    } catch (e) {}

    const detailsRes = http.get(getApiUrl(`/tournaments/${slug}`), {
      headers: CONFIG.DEFAULT_HEADERS,
      tags: { name: 'GET /api/v1/tournaments/:slug' },
    });
    check(detailsRes, {
      'tournament details status 200': (r) => r.status === 200,
    });
  });

  sleep(Math.random() * 1.5 + 0.5);

  // 3. API - Academies & Leaderboard (authenticated if token provided)
  group('3. Academies & Leaderboard', function () {
    const acadRes = http.get(getApiUrl('/academies'), {
      headers: CONFIG.DEFAULT_HEADERS,
      tags: { name: 'GET /api/v1/academies' },
    });
    check(acadRes, {
      'academies status 200': (r) => r.status === 200,
    });

    // Leaderboard endpoint enforces authentication on production
    const lbRes = http.get(getApiUrl('/leaderboard'), {
      headers: authHeaders,
      tags: { name: 'GET /api/v1/leaderboard' },
    });
    leaderboardDuration.add(lbRes.timings.duration);

    check(lbRes, {
      'leaderboard status 200': (r) => r.status === 200,
    });
  });

  sleep(Math.random() * 2 + 1);
}
