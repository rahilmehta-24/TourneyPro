// load_tests/scenarios/public-browse.js
import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Trend } from 'k6/metrics';
import { CONFIG, getUrl, getApiUrl } from '../config.js';

// Custom metrics to monitor response times by route category
const tournamentBrowseDuration = new Trend('browse_tournaments_duration');
const leaderboardDuration = new Trend('leaderboard_duration');

export const options = {
  stages: [
    { duration: '20s', target: 10 }, // Ramp up to 10 VUs
    { duration: '40s', target: 30 }, // Ramp up to 30 VUs
    { duration: '30s', target: 50 }, // Peak at 50 VUs
    { duration: '20s', target: 0 },  // Ramp down to 0 VUs
  ],
  thresholds: {
    ...CONFIG.THRESHOLDS,
    browse_tournaments_duration: ['p(95)<400'],
    leaderboard_duration: ['p(95)<400'],
  },
};

export default function () {
  group('1. Browse Public Tournaments', function () {
    const res = http.get(getApiUrl('/tournaments'), {
      headers: CONFIG.DEFAULT_HEADERS,
      tags: { name: 'GET /api/v1/tournaments' },
    });
    tournamentBrowseDuration.add(res.timings.duration);

    check(res, {
      'tournaments status 200': (r) => r.status === 200,
      'has tournament list': (r) => {
        try {
          const body = JSON.parse(r.body);
          return body.tournaments !== undefined || Array.isArray(body);
        } catch (e) {
          return false;
        }
      },
    });

    // If test-tournament exists, fetch details and order of play
    const detailsRes = http.get(getApiUrl('/tournaments/test-tournament'), {
      headers: CONFIG.DEFAULT_HEADERS,
      tags: { name: 'GET /api/v1/tournaments/:slug' },
    });
    check(detailsRes, {
      'details status 200 or 404': (r) => r.status === 200 || r.status === 404,
    });
  });

  sleep(Math.random() * 1.5 + 0.5); // Think time: 0.5s - 2s

  group('2. Browse Academies', function () {
    const res = http.get(getApiUrl('/academies'), {
      headers: CONFIG.DEFAULT_HEADERS,
      tags: { name: 'GET /api/v1/academies' },
    });
    check(res, {
      'academies status 200': (r) => r.status === 200,
    });
  });

  sleep(Math.random() * 1.5 + 0.5);

  group('3. View Leaderboard & Announcements', function () {
    const lbRes = http.get(getApiUrl('/leaderboard'), {
      headers: CONFIG.DEFAULT_HEADERS,
      tags: { name: 'GET /api/v1/leaderboard' },
    });
    leaderboardDuration.add(lbRes.timings.duration);

    check(lbRes, {
      'leaderboard status 200': (r) => r.status === 200,
    });

    const annRes = http.get(getApiUrl('/announcements'), {
      headers: CONFIG.DEFAULT_HEADERS,
      tags: { name: 'GET /api/v1/announcements' },
    });
    check(annRes, {
      'announcements status 200': (r) => r.status === 200,
    });
  });

  sleep(Math.random() * 2 + 1);
}
