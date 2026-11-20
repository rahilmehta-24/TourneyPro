# The Baseline Society — RESTful API Specification (API.md)

**Document Status:** Approved  
**Source of Truth:** Inherits from [`DATABASE.md`](DATABASE.md) and [`ARCHITECTURE.md`](ARCHITECTURE.md)  
**API Version:** `v1` (hardened revision)  
**Base URL:** `/api/v1`  
**Authentication Scheme:** HTTP Bearer Authentication (JSON Web Tokens - JWT)  
**Last Updated:** November 2026  

---

## 1. Global API Conventions

### 1.1 Content Negotiation & Formatting
* All API endpoints receive and return `application/json; charset=utf-8`.
* All timestamps returned by the API conform to ISO 8601 UTC format: `YYYY-MM-DDTHH:MM:SSZ`.
* Dates conform to `YYYY-MM-DD`.

### 1.2 Standard JSON Envelope
Every response carries a boolean `success`. Resource payloads are returned as named top-level keys next to `success` (for example `tournament`, `tournaments`, `matches`, `access_token`); the optional `message` is human-readable.

**Success Response:**
```json
{
  "success": true,
  "message": "Operation completed successfully",
  "tournament": { "...": "..." }
}
```

**Error Response:**
```json
{
  "success": false,
  "message": "Human-readable explanation of error condition"
}
```

> **Known deviation:** the live-score feed (§4.4) is a legacy shape without `success`. Clients must tolerate both. New endpoints must always include `success`. Error messages must never reveal stack traces, SQL, or whether a username exists.

### 1.3 HTTP Status Codes
* `200 OK`: Request succeeded, response body contains requested entity.
* `201 Created`: Entity successfully created.
* `400 Bad Request`: Missing required payload fields or invalid format/rules.
* `401 Unauthorized`: Missing, expired, or malformed JWT Bearer token.
* `403 Forbidden`: Authenticated user lacks permission (insufficient RBAC role, BOLA ownership failure, or active participant conflict of interest).
* `404 Not Found`: Target tournament, category, or match does not exist.
* `409 Conflict`: Concurrency collision (submitted `lock_version` does not match database version).
* `429 Too Many Requests`: Rate limit exceeded (see §5). Response includes a `Retry-After` header.
* `500 Internal Server Error`: Unhandled server exception (automatically rolled back in DB).

---

## 2. Authentication, RBAC & Concurrency Control

API authentication is powered by `Flask-JWT-Extended`. All mutating operations require a valid JWT in the `Authorization` header:

```http
Authorization: Bearer <eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...>
```

### 2.1 Token Policy (required hardening)
* **Signing secret:** `JWT_SECRET_KEY` must be a separate high-entropy secret (>= 32 random bytes), never the Flask session `SECRET_KEY`. Algorithm pinned to `HS256`; tokens with `alg: none` or any other algorithm are rejected.
* **Lifetime:** access tokens expire in 60 minutes by default (`JWT_ACCESS_TOKEN_EXPIRES`). Long-lived tokens are not issued; refresh tokens, if introduced, must be rotating and revocable.
* **Per-request user check:** every protected request reloads the user and rejects accounts whose role is `deleted`. Roles are never trusted from token claims.
* **Transport:** tokens are sent only over HTTPS and are never placed in URLs or logs.
* **CSRF exemption:** the API Blueprint (`/api/v1/*`) is exempt from CSRF and must not accept session cookies as authentication.

### 2.2 Hierarchical RBAC & Delegated Staff
Operations evaluate the caller through `check_tournament_access(tournament, min_role=..., user=user)`. Roles, lowest to highest:

| Rank | Role | Source | Typical API capability |
| :---: | :--- | :--- | :--- |
| 10 | `scorer` | `tournament_staff.role` | Report live scores |
| 20 | `official` | `tournament_staff.role` | Complete matches, walkovers, retirements, reset a match to `pending` |
| 30 | `manager` | `tournament_staff.role` | Scheduling, check-in, seeds, court assignment |
| 40 | `owner` | `tournaments.user_id` | Settings, staff, PINs, draw publication |
| 100 | `superadmin` | `users.role` | Global override (always audit-logged) |

* Legacy names `tournament_admin`, `desk`, `umpire` are deprecated aliases (`tournament_admin`/`desk` map to `manager`, `umpire` maps to `scorer`) and must be migrated in `tournament_staff`.
* The check is **fail-closed**: an unknown role or unknown `min_role` returns `403`.
* **Court PIN sessions are web-only.** They are never accepted by the REST API.
* **Anti-Conflict of Interest Protection:** if the authenticated user is an active participant in the target match (player, doubles partner, team member in a rubber lineup, or captain of a competing team), score reporting is blocked with `HTTP 403 Forbidden`.
* **Optimistic Concurrency Control:** `lock_version` is **required** on every score-changing request. A missing value returns `400`; a stale value returns `409 Conflict`. The update is applied atomically (`UPDATE ... WHERE id = :id AND lock_version = :v`), so two simultaneous requests can never both succeed.

---

## 3. Serialization Schemas (Marshmallow)

Defined in [`app/domain/schemas.py`](app/domain/schemas.py). Schemas are split by audience so private data can never leak by accident:

* **`UserSchema` (private, never public):** `id`, `username`, `role`, `created_at`. `email` is returned only to the user themselves or a superadmin.
* **`PublicParticipantSchema`:** `id`, `name`, `seed`, `eliminated`, `final_rank`. Excludes `email`, `mobile`, `dob`, `payment_status`, `payment_method`, `checked_in`, `manual_seed`.
* **`StaffParticipantSchema`** (owner/manager/official only): adds `manual_seed`, `checked_in`, `payment_status`.
* **`MatchSchema`:** `id`, `round`, `match_number`, `status`, `score1`, `score2`, `winner_id`, `court_name`, `scheduled_time`, `is_not_before`, `participant1`, `participant2` (public participant schema).
* **`CategorySchema`:** `id`, `name`, `format`, `status`, `gender`, `age_category`, `draw_published`. `matches` and `participants` are included only when the draw is published or the caller has staff access.
* **`TournamentSchema`:** `id`, `name`, `url_slug`, `description`, `status`, `start_date`, `end_date`, `num_courts`, `categories`. Excludes `payment_upi_id` unless registration is open.

> **Rule:** use `Schema(only=...)` / explicit public schemas; never serialize a model with `fields = "__all__"` in a public endpoint. Personal data of minors (age categories U10 to U18) must never appear in public responses beyond display name.

---

## 4. Endpoint Specifications

### 4.1 Authentication Endpoints

#### 4.1.1 User Registration
* **Endpoint:** `POST /api/v1/auth/register`
* **Access:** Public
* **Request Payload:**
  ```json
  {
    "username": "coach_serena",
    "email": "serena@tennisacademy.com",
    "password": "SecurePassword123!"
  }
  ```
* **Response (201 Created):**
  ```json
  {
    "success": true,
    "access_token": "eyJhbGciOiJIUzI1Ni...",
    "user": {
      "id": 14,
      "username": "coach_serena",
      "role": "user"
    }
  }
  ```

#### 4.1.2 User Login
* **Endpoint:** `POST /api/v1/auth/login`
* **Access:** Public
* **Request Payload:**
  ```json
  {
    "username": "coach_serena",
    "password": "SecurePassword123!"
  }
  ```
* **Response (200 OK):**
  ```json
  {
    "success": true,
    "access_token": "eyJhbGciOiJIUzI1Ni...",
    "user": {
      "id": 14,
      "username": "coach_serena",
      "role": "user"
    }
  }
  ```

* **Hardening:** registration is rate-limited (5 per hour per IP), enforces a minimum password length of 10, rejects the 1,000 most common passwords, normalizes the email to lower case, and returns a generic error for duplicates so account existence is not revealed. New accounts always get role `user`; `role` supplied in the payload is ignored.
* **Login hardening:** 10 attempts per 15 minutes per IP + username, generic `401 "Invalid credentials"` for both unknown user and wrong password, constant-time hash check, and a short lockout after repeated failures. Successful logins never include the password hash.

---

### 4.2 Tournament Endpoints

#### 4.2.1 List Tournaments
* **Endpoint:** `GET /api/v1/tournaments`
* **Access:** Public
* **Response (200 OK):**
  ```json
  {
    "success": true,
    "tournaments": [
      {
        "id": 1,
        "name": "State Tennis Championship 2026",
        "url_slug": "state-tennis-2026",
        "status": "in_progress",
        "start_date": "2026-11-01",
        "end_date": "2026-11-04",
        "num_courts": 4
      }
    ]
  }
  ```

* **Visibility & paging:** only tournaments with `is_private = false` and status other than `setup` are listed publicly. Supports `?page=1&per_page=20` (max 100). Private tournaments are returned only to their owner, staff, or superadmin.

#### 4.2.2 Get Tournament Details by Slug
* **Endpoint:** `GET /api/v1/tournaments/<slug>`
* **Access:** Public
* **Response (200 OK):**
  ```json
  {
    "success": true,
    "tournament": {
      "id": 1,
      "name": "State Tennis Championship 2026",
      "url_slug": "state-tennis-2026",
      "description": "Annual state championship open to all registered players.",
      "status": "in_progress",
      "categories": [
        {
          "id": 10,
          "name": "Men's Open Singles",
          "format": "single_elimination",
          "status": "in_progress"
        }
      ]
    }
  }
  ```

#### 4.2.3 Get Category Details
* **Endpoint:** `GET /api/v1/tournaments/<slug>/categories/<int:category_id>`
* **Access:** Public
* **Draft-draw guard:** when `draw_published = false` and the caller lacks staff access, the endpoint returns `403` with `"Draws for this event are being finalized by the tournament committee"` and **no** participants or matches.
* **Response (200 OK):** Returns the category object with public participants and bracket matches (staff callers also receive staff-only fields).

---

### 4.3 Match Management & Score Reporting

#### 4.3.1 Get Category Fixtures
* **Endpoint:** `GET /api/v1/matches/category/<int:category_id>`
* **Access:** Public
* **Response (200 OK):**
  ```json
  {
    "success": true,
    "matches": [
      {
        "id": 105,
        "round": 1,
        "match_number": 1,
        "status": "completed",
        "score1": "6-4, 6-3",
        "score2": "",
        "winner_id": 42,
        "court_name": "Court 1",
        "participant1": { "id": 42, "name": "Rohan Bopanna", "seed": 1 },
        "participant2": { "id": 55, "name": "Sumit Nagal", "seed": null }
      }
    ]
  }
  ```

* **Draft-draw guard:** applies exactly as in §4.2.3. Fixtures of unpublished categories are never returned to public callers.

#### 4.3.2 Report Match Score & Progression
* **Endpoint:** `POST /api/v1/matches/<int:match_id>/report`
* **Access:** Authenticated (`owner`, `manager`, `official`, `scorer`, or `superadmin`). Resetting to `pending` requires `official` or higher.
* **Headers:** `Authorization: Bearer <token>`
* **Action Types:**
  1. `complete_match`: Records final score, marks match completed, and advances winner to downstream fixture.
  2. `live_score`: Updates current score without finalizing match. Status set to `in_progress`.
  3. `pending`: Resets match back to pending, clearing scores and winner.
* **Request Payload (Complete Match):**
  ```json
  {
    "action_type": "complete_match",
    "winner_id": 42,
    "score1": "6-4, 7-6(5)",
    "score2": "",
    "lock_version": 1
  }
  ```
  `lock_version` is mandatory. `score1`/`score2` are validated against a strict pattern and a 50-character limit; request bodies above 8 KB are rejected.
* **Validation & Security Enforcements (evaluated in this order):**
  1. **Authentication:** missing/expired/invalid JWT returns `401`; deleted users return `401`.
  2. **RBAC & BOLA:** `check_tournament_access(match.tournament, min_role="scorer", user=user)`. The match must belong to the tournament resolved from its own record (never from a client-supplied tournament id).
  3. **Conflict of Interest Guard:** `check_scoring_conflict_of_interest(match, user)` raises `403` for active players, doubles partners, rubber-lineup players, and competing team captains:
     ```json
     { "success": false, "message": "Conflict of interest: Active participants cannot officiate or score their own matches." }
     ```
  4. **Input validation:** `action_type` must be one of the three allowed values; `winner_id` must equal `participant1_id` or `participant2_id`; scoreline must satisfy the format rules (tennis sets, or $G_1 + G_2 = 7$ for rubbers); an already `completed` match cannot be completed again (prevents double advancement).
  5. **Optimistic Concurrency Control:** `lock_version` is required and compared atomically. Mismatch returns `409`:
     ```json
     { "success": false, "message": "Conflict: Match was updated by another official. Please refresh and try again." }
     ```
  6. **Progression Guard:** `check_match_progression_allowed(match)`. Incomplete feeder matches return `HTTP 400 Bad Request`.
  7. **Automatic Bracket Progression:** the winner is advanced via `fmt.advance_match()`; for `group_stage` / `round_robin`, `recalculate_all_group_stats()` runs.
  8. **Audit:** every `complete_match`, correction, and `pending` reset writes an `AuditLog` row (actor, match, before/after scores, `lock_version`). Superadmin overrides are always flagged.
* **Response (200 OK):**
  ```json
  {
    "success": true,
    "message": "Match completed",
    "lock_version": 2
  }
  ```

---

### 4.4 Real-Time Live Score Polling

#### 4.4.1 Tournament Live Scores Feed
* **Endpoint:** `GET /api/v1/live/<slug>/scores`
* **Access:** Public (published draws of public tournaments only)
* **Polling:** every 5 seconds by spectator bracket views.
* **Caching (required):** responses send `Cache-Control: public, max-age=3, s-maxage=3` and a strong `ETag` derived from the highest `lock_version`/`completed_at` of the tournament's matches; a matching `If-None-Match` returns `304`. This lets a CDN absorb thousands of spectators with one database read every few seconds.
* **Content rules:** matches from categories with `draw_published = false` are excluded; only the fields below are returned (no participant contact data).
* **Response (200 OK):**
  ```json
  {
    "tournament": "state-tennis-2026",
    "matches": [
      {
        "id": 105,
        "status": "in_progress",
        "score1": "4",
        "score2": "3",
        "winner_id": null,
        "p1": "Rohan Bopanna",
        "p2": "Sumit Nagal",
        "court": "Court 1",
        "scheduled_time": "14:30"
      }
    ]
  }
  ```
* **Future:** when WebSocket/SSE push is introduced (see [`PLAN.md`](PLAN.md) WP 2.1), polling remains the fallback transport.

---

### 4.5 Academy Federation, Notifications & Leaderboard

#### 4.5.1 Browse Verified Academies
* **Endpoint:** `GET /api/v1/academies`
* **Access:** Public
* **Query Parameters:** `city` (optional), `state` (optional), `sport` (optional).
* **Response (200 OK):**
  ```json
  {
    "success": true,
    "academies": [
      {
        "id": 1,
        "name": "Apex Tennis Academy",
        "url_slug": "apex-tennis-academy",
        "city": "Ahmedabad",
        "state": "Gujarat",
        "status": "ACTIVE",
        "logo_url": "/static/uploads/tournaments/logos/apex.png"
      }
    ]
  }
  ```

#### 4.5.2 Apply for Academy Verification
* **Endpoint:** `POST /api/v1/academies/apply`
* **Access:** Authenticated (`Authorization: Bearer <token>`)
* **Request Payload:** `name` (required), `contact_email` (required), `description`, `address`, `city`, `state`, `country`, `contact_phone`, `sports_offered`, `website_url`.
* **Response (201 Created):**
  ```json
  {
    "success": true,
    "message": "Academy verification application submitted",
    "application_id": 4
  }
  ```

#### 4.5.3 Check Academy Application Status
* **Endpoint:** `GET /api/v1/academies/application-status`
* **Access:** Authenticated (`Authorization: Bearer <token>`)
* **Response (200 OK):**
  ```json
  {
    "success": true,
    "application": {
      "id": 4,
      "name": "Apex Tennis Academy",
      "status": "PENDING",
      "submitted_at": "2026-11-17T10:00:00Z",
      "rejection_reason": null
    }
  }
  ```

#### 4.5.4 In-App Notifications Feed
* **Endpoint:** `GET /api/v1/notifications`
* **Access:** Authenticated (`Authorization: Bearer <token>`)
* **Response (200 OK):**
  ```json
  {
    "success": true,
    "unread_count": 2,
    "notifications": [
      {
        "id": 12,
        "title": "Registration Approved! 🎾",
        "body": "Your entry for National Open (Men's Singles) has been approved.",
        "notification_type": "registration_update",
        "is_read": false,
        "created_at": "2026-11-17T10:30:00Z"
      }
    ]
  }
  ```

#### 4.5.5 Mark Notification Read
* **Endpoint:** `POST /api/v1/notifications/<id>/read`
* **Access:** Authenticated (`Authorization: Bearer <token>`)
* **Response (200 OK):**
  ```json
  {
    "success": true,
    "message": "Notification marked as read"
  }
  ```

#### 4.5.6 Notification Preferences
* **Endpoint:** `GET /api/v1/users/notification-preferences` & `PUT /api/v1/users/notification-preferences`
* **Access:** Authenticated (`Authorization: Bearer <token>`)
* **Payload (PUT):** `notify_match_called`, `notify_draw_published`, `notify_registration_updates`, `notify_match_results`, `notify_academy_announcements`.

#### 4.5.7 Qualified Official Leaderboard
* **Endpoint:** `GET /api/v1/leaderboard`
* **Access:** Public
* **Query Parameters:** `category` (optional, canonical Age Category), `gender` (optional), `limit` (default 50, max 100).
* **Qualification Rule:** Only players with `total_points > 0`, `matches_played > 0`, or active tournament participation are included. Zero-history and dummy accounts are excluded.
* **Response (200 OK):**
  ```json
  {
    "success": true,
    "rankings": [
      {
        "rank": 1,
        "id": 42,
        "name": "Rafael Nadal",
        "points": 1450,
        "age_category": "Open",
        "gender": "Male",
        "academy": "Apex Tennis Academy",
        "matches_played": 14,
        "matches_won": 13,
        "win_rate": 92.9
      }
    ]
  }
  ```

### 4.6 Flexible Tournament Registration & Bulk Import

#### 4.6.1 Finalize Category Playing Format
* **Endpoint:** `POST /api/v1/tournaments/<slug>/categories/<category_id>/format`
* **Access:** Organizer / Admin (`Authorization: Bearer <token>`)
* **Payload:**
  ```json
  {
    "format": "single_elimination",
    "scoring_format": "games",
    "num_sets": 3,
    "games_per_set": 6
  }
  ```
* **Response (200 OK):**
  ```json
  {
    "success": true,
    "message": "Playing format finalized successfully. Existing registrations preserved.",
    "category": {
      "id": 1,
      "name": "Men's Singles",
      "format": "single_elimination",
      "format_status": "FINALIZED"
    }
  }
  ```

#### 4.6.2 Toggle Category Registration Status
* **Endpoint:** `PATCH /api/v1/tournaments/<slug>/categories/<category_id>/registration-status`
* **Access:** Organizer / Admin (`Authorization: Bearer <token>`)
* **Payload:**
  ```json
  {
    "status": "CLOSED"
  }
  ```
* **Response (200 OK):**
  ```json
  {
    "success": true,
    "category_id": 1,
    "is_registration_open": false,
    "registration_status": "CLOSED"
  }
  ```

#### 4.6.3 Download CSV Import Template
* **Endpoint:** `GET /api/v1/tournaments/<slug>/import/template`
* **Access:** Organizer / Admin (`Authorization: Bearer <token>`)
* **Response:** CSV attachment with sample rows and standard columns.

#### 4.6.4 Upload and Validate CSV File
* **Endpoint:** `POST /api/v1/tournaments/<slug>/import/upload`
* **Access:** Organizer / Admin (`Authorization: Bearer <token>`)
* **Form Data:** `csv_file` (file)
* **Response (200 OK):**
  ```json
  {
    "success": true,
    "batch_id": 12,
    "total_rows": 10,
    "valid_count": 8,
    "invalid_count": 1,
    "duplicate_count": 1,
    "preview_valid": [...],
    "preview_errors": [...]
  }
  ```

#### 4.6.5 Confirm Bulk Import
* **Endpoint:** `POST /api/v1/tournaments/<slug>/import/confirm`
* **Access:** Organizer / Admin (`Authorization: Bearer <token>`)
* **Payload:**
  ```json
  {
    "batch_id": 12
  }
  ```
* **Response (200 OK):**
  ```json
  {
    "success": true,
    "message": "Successfully imported 8 participant(s).",
    "imported_count": 8,
    "batch_id": 12
  }
  ```

#### 4.6.6 Download Import Error Report
* **Endpoint:** `GET /api/v1/tournaments/<slug>/import/<batch_id>/errors`
* **Access:** Organizer / Admin (`Authorization: Bearer <token>`)
* **Response:** CSV report with sanitized fields and exact failure reasons.

#### 4.6.7 Get Import History
* **Endpoint:** `GET /api/v1/tournaments/<slug>/import/history`
* **Access:** Organizer / Admin (`Authorization: Bearer <token>`)
* **Response (200 OK):**
  ```json
  {
    "success": true,
    "history": [
      {
        "id": 12,
        "filename": "summer_registrations.csv",
        "total_rows": 10,
        "valid_rows": 8,
        "imported_rows": 8,
        "status": "COMPLETED",
        "created_at": "2026-11-20T10:00:00"
      }
    ]
  }
  ```

---

## 5. Rate Limits (required hardening)

| Scope | Limit | Key |
| :--- | :--- | :--- |
| `POST /auth/login` | 10 / 15 min | IP + username |
| `POST /auth/register` | 5 / hour | IP |
| `POST /matches/<id>/report` | 120 / min | user |
| Public `GET` endpoints | 120 / min | IP (cache-friendly endpoints exempt when served from CDN) |
| `GET /live/<slug>/scores` | 30 / min | IP |

Exceeded limits return `429` with `Retry-After`. Limiter storage must be shared (Redis or database), not per-process memory, so limits hold across Gunicorn workers and serverless instances. Behind a proxy or Vercel, the real client IP is read through `ProxyFix` / `X-Forwarded-For` from a trusted hop only.

## 6. CORS & Security Headers
* CORS is disabled by default. If a separate web or mobile origin needs access, allow-list exact origins; never `*` with credentials.
* All API responses send `X-Content-Type-Options: nosniff`, `Cache-Control: no-store` (except the cacheable public endpoints above), and are served only over HTTPS with HSTS.
