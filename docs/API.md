# TourneyPro — RESTful API Specification (API.md)

**Document Status:** Approved  
**Source of Truth:** Inherits from [`DATABASE.md`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/DATABASE.md) and [`ARCHITECTURE.md`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/ARCHITECTURE.md)  
**API Version:** `v1`  
**Base URL:** `/api/v1`  
**Authentication Scheme:** HTTP Bearer Authentication (JSON Web Tokens - JWT)  
**Last Updated:** October 2026  

---

## 1. Global API Conventions

### 1.1 Content Negotiation & Formatting
* All API endpoints receive and return `application/json; charset=utf-8`.
* All timestamps returned by the API conform to ISO 8601 UTC format: `YYYY-MM-DDTHH:MM:SSZ`.
* Dates conform to `YYYY-MM-DD`.

### 1.2 Standard JSON Envelope
Responses adhere to a standardized JSON structure:

**Success Response Envelope:**
```json
{
  "success": true,
  "message": "Operation completed successfully",
  "data": { ... }
}
```

**Error Response Envelope:**
```json
{
  "success": false,
  "message": "Human-readable explanation of error condition"
}
```

### 1.3 HTTP Status Codes
* `200 OK`: Request succeeded, response body contains requested entity.
* `201 Created`: Entity successfully created.
* `400 Bad Request`: Missing required payload fields or invalid format/rules.
* `401 Unauthorized`: Missing, expired, or malformed JWT Bearer token.
* `403 Forbidden`: Authenticated user lacks permission (RBAC role inadequate or BOLA ownership failure).
* `404 Not Found`: Target tournament, category, or match does not exist.
* `500 Internal Server Error`: Unhandled server exception (automatically rolled back in DB).

---

## 2. Authentication & Authorization

API authentication is powered by `Flask-JWT-Extended`. All mutating operations require a valid JWT token passed in the `Authorization` HTTP header:

```http
Authorization: Bearer <eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...>
```

* **CSRF Exemption:** The API Blueprint (`/api/v1/*`) is explicitly exempted from CSRF cookie requirements, relying strictly on stateless token authorization.
* **Broken Object Level Authorization (BOLA/IDOR) Protection:** When mutating tournament matches or configurations, the API verifies that `current_user.id == tournament.user_id` (unless `current_user.role == 'superadmin'`). Unauthorized attempts are rejected with `HTTP 403 Forbidden`.

---

## 3. Serialization Schemas (Marshmallow)

Defined in [`app/domain/schemas.py`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/app/domain/schemas.py):

* **`UserSchema`:** Fields: `id`, `username`, `email`, `role`, `created_at`.
* **`ParticipantSchema`:** Fields: `id`, `name`, `seed`, `manual_seed`, `checked_in`, `eliminated`, `final_rank`, `payment_status`.
* **`MatchSchema`:** Fields: `id`, `round`, `match_number`, `status`, `score1`, `score2`, `winner_id`, `court_name`, `scheduled_time`, `is_not_before`, `participant1` (`ParticipantSchema`), `participant2` (`ParticipantSchema`).
* **`CategorySchema`:** Fields: `id`, `name`, `format`, `status`, `gender`, `age_category`, `matches` (`MatchSchema` list), `participants` (`ParticipantSchema` list).
* **`TournamentSchema`:** Fields: `id`, `name`, `url_slug`, `description`, `status`, `start_date`, `end_date`, `num_courts`, `categories` (`CategorySchema` list).

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
* **Response (200 OK):** Returns detailed category object with participants and bracket matches.

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

#### 4.3.2 Report Match Score & Progression
* **Endpoint:** `POST /api/v1/matches/<int:match_id>/report`
* **Access:** Authenticated (`admin` or `superadmin` role with tournament ownership)
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
    "score2": ""
  }
  ```
* **Validation & Security Enforcements:**
  * **BOLA Verification:** Checks `match.tournament.user_id == current_user.id`.
  * **Progression Guard:** Calls `check_match_progression_allowed(match)`. If feeder matches are incomplete, returns `HTTP 400 Bad Request`.
  * **Automatic Bracket Progression:** Winner is advanced to parent/downstream fixture via `fmt.advance_match()`.
  * **Group Standings Sync:** If format is `group_stage` or `round_robin`, triggers `recalculate_all_group_stats()`.
* **Response (200 OK):**
  ```json
  {
    "success": true,
    "message": "Match completed"
  }
  ```

---

### 4.4 Real-Time Live Score Polling

#### 4.4.1 Tournament Live Scores Feed
* **Endpoint:** `GET /api/v1/live/<slug>/scores`
* **Access:** Public
* **Rate Recommendation:** Polled every 5 seconds by spectator bracket views.
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
