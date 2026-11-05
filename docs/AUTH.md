# TourneyPro — Authentication, Authorization & Security Architecture (AUTH.md)

**Document Status:** Approved  
**Source of Truth:** Inherits from [`FEATURES.md`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/FEATURES.md), [`API.md`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/API.md), and [`ARCHITECTURE.md`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/ARCHITECTURE.md)  
**Security Standard:** OWASP Top 10 Compliant (ASVS 4.0 Level 2)  
**Authentication Handlers:** Flask-WTF (Web Sessions) & Flask-JWT-Extended (Headless API)  
**Last Updated:** October 2026  

---

## 1. Dual Authentication Architecture

TourneyPro enforces a dual authentication model tailored to its hybrid SSR and headless REST API structure:

```
                                   ┌─────────────────────────────────────────┐
                                   │            Incoming Request             │
                                   └────────────────────┬────────────────────┘
                                                        │
                           ┌────────────────────────────┴────────────────────────────┐
                           ▼                                                         ▼
            ┌───────────────────────────────┐                         ┌───────────────────────────────┐
            │       Web Client (SSR)        │                         │      REST API (/api/v1/)      │
            └──────────────┬────────────────┘                         └──────────────┬────────────────┘
                           │                                                         │
                           ▼                                                         ▼
            ┌───────────────────────────────┐                         ┌───────────────────────────────┐
            │ - Signed Session Cookie       │                         │ - Stateless JWT Bearer Token  │
            │ - Flask-WTF CSRF Token        │                         │ - CSRF Exempt                 │
            │ - Session Timeout / Renewal   │                         │ - Token Expiration Check      │
            └──────────────┬────────────────┘                         └──────────────┬────────────────┘
                           │                                                         │
                           └────────────────────────────┬────────────────────────────┘
                                                        │
                                                        ▼
                                   ┌─────────────────────────────────────────┐
                                   │         RBAC & BOLA Authorization       │
                                   │  - Role Verification (@role_required)   │
                                   │  - Ownership Guard (check_ownership)   │
                                   └─────────────────────────────────────────┘
```

---

## 2. Role-Based Access Control (RBAC) & Permission Architecture

TourneyPro enforces a multi-tiered authorization model separating platform-wide system roles from tournament-scoped staff and temporary court umpires:

### 2.1 Platform System Roles (`users.role`)
1. **`superadmin`:** Platform administrators with global override authority across all tournaments, user accounts, audit trails, and database sync tools.
2. **`admin`:** Tournament organizers and academy directors authorized to create tournaments, configure categories, manage finances, and oversee operations.
3. **`user` / `player`:** Registered athletes, coaches, and team captains who self-register, manage player profiles, submit nominations, and compete.
4. **Guest (Unauthenticated Public):** Public spectators capable of browsing tournaments, viewing public brackets, tracking live scores, and downloading published Draw & Order of Play PDFs.

### 2.2 Tournament-Scoped Staff Roles (`TournamentStaff`)
Tournament Owners can appoint other registered users into specific tournament roles via [`TournamentStaff`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/app/domain/models.py):
- **`manager`:** Operational management over courts, match schedules, delays, and scores.
- **`official`:** Chief referee decisions, walkovers, retirements, dispute resolution, and scoring.
- **`scorer`:** Match score reporting and live court updates.

### 2.3 Temporary Court Access PINs
Volunteer chair umpires and desk staff can score matches on court tablets or phones without creating an account:
- Organizers generate a 6-digit PIN with a validity duration (8h, 24h, 48h) tied to an optional court designation.
- The umpire authenticates at `/t/<slug>/score-login` using the PIN.
- The system establishes a secure court session (`session['court_pin_auth']`) valid until expiration or explicit logout.

### 2.4 Comprehensive Permissions Matrix

| Operational Capability | Guest | Player / User | Team Captain | Court Umpire (PIN) | Scorer (Staff) | Official / Manager | Organizer (Owner) | Superadmin |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| Browse Tournaments & Live Scores | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Submit Tournament Registration | ✅ (Guest) | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ | ✅ |
| Download Published Draw PDF | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Download Draft (Unpublished) Draw PDF | ❌ (403) | ❌ (403) | ❌ (403) | ❌ (403) | ❌ (403) | ❌ (403) | ✅ | ✅ |
| Toggle Draw Publish Status | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| Export Participants Desk Roster PDF | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| Export Matches & Standings CSV | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| Nominate Team Rubber Lineup | ❌ | ❌ | ✅ (Own Team) | ❌ | ❌ | ❌ | ✅ | ✅ |
| Appoint Tournament Staff | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| Generate 6-Digit Court Access PIN | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| Report Live Match Scores | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Override Score (Competitor in Match) | ❌ (Blocked) | ❌ (Blocked) | ❌ (Blocked) | ❌ (Blocked) | ❌ (Blocked) | ❌ (Blocked) | ❌ (Blocked) | ✅ |
| Elevate Platform User to Admin | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |

---

## 3. Concurrency & Integrity Defenses

### 3.1 Anti-Conflict of Interest Protection
To protect athletic integrity, playing competitors are strictly blocked from recording or altering scores for their own matches:
- Guard function: `check_scoring_conflict_of_interest(match, user)` in [`app/web/controllers/auth.py`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/app/web/controllers/auth.py).
- Inspects both competitors' linked `Player` IDs against `user.id`.
- If a match participant attempts to score their match, the request is rejected with a **403 Forbidden** error.

### 3.2 Optimistic Concurrency Control (`lock_version`)
Simultaneous score reporting by desk coordinators and court umpires is guarded via optimistic locking:
- `Match.lock_version` integer counter increments with every score update.
- The reporting form transmits the expected `lock_version`.
- If the database `lock_version` does not match, a **409 Conflict** error is returned, preventing silent score overwrites.

### 3.3 Team Captain Lineup Nomination Window
- Guard function: `check_fixture_lineup_access(fixture, user)` in [`app/web/controllers/auth.py`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/app/web/controllers/auth.py).
- Captains can only nominate players for their own squad (opposing team fields are strictly isolated).
- Lineups automatically lock **15 minutes** prior to fixture start (`scheduled_time - 15 minutes`).

### 3.4 Multi-Tenant Academy Isolation
- Guard function: `check_academy_access(academy, require_admin=False)` in [`app/web/controllers/auth.py`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/app/web/controllers/auth.py).
- Ensures academy announcements and member rosters can only be modified by approved academy administrators or superadmins.

---

## 4. Broken Object Level Authorization (BOLA/IDOR) Defense

A critical security vulnerability in multi-tenant tournament software is BOLA (Broken Object Level Authorization), where an authenticated organizer attempts to alter fixtures or settings belonging to another organizer by manipulating IDs in the URL.

TourneyPro neutralizes BOLA at both the controller and API layers:

### 4.1 Web Controller Defense (`check_tournament_access`)
Defined in [`app/web/controllers/auth.py`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/app/web/controllers/auth.py):
```python
def check_tournament_access(tournament, min_role="scorer"):
    # 1. Superadmin has global override
    # 2. Tournament Owner has full ownership
    # 3. TournamentStaff role check (Manager >= Official >= Scorer)
    # 4. Active Court Access PIN session verification
```
Every mutation route in `tournament_bp` and `category_bp` calls this guard prior to executing any state alteration.

### 4.2 API Layer Defense
Defined in [`app/api/matches.py`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/app/api/matches.py):
```python
@api_bp.route('/matches/<int:match_id>/report', methods=['POST'])
@jwt_required()
def report_match(match_id):
    current_user_id = int(get_jwt_identity())
    user = User.query.get(current_user_id)
    match = Match.query.get_or_404(match_id)
    
    # Tournament ownership and staff delegation guard:
    check_tournament_access(match.tournament, min_role="scorer")
    check_scoring_conflict_of_interest(match, user)
```

---

## 5. Cryptographic Standards & Password Security

* **Password Hashing:** Passwords are hashed using Werkzeug's `generate_password_hash` implementation of **PBKDF2-HMAC-SHA256** with salt length of 16 bytes and 260,000 iterations:
  ```python
  def set_password(self, password):
      from werkzeug.security import generate_password_hash
      self.password_hash = generate_password_hash(password)
  ```
* **Password Verification:** Constant-time comparison via `check_password_hash` prevents timing attacks.
* **Session Cryptography:** Flask session cookies are signed using `SECRET_KEY` with `HttpOnly=True`, `SameSite='Lax'`, and secure flag when running over HTTPS.

---

## 6. Superadmin Bootstrapping

On fresh deployments or container starts, the application automatically ensures an administrative user exists without requiring interactive shell access:

* Implemented in `bootstrap_superadmin()` in [`app/web/controllers/auth.py`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/app/web/controllers/auth.py).
* Checks if `User.query.count() == 0`.
* If empty, provisions the superadmin using environment variables:
  * `SUPERADMIN_USERNAME` (Default: `superadmin`)
  * `SUPERADMIN_PASSWORD` (Default: `adminpassword`)
* Sets user `role = 'superadmin'`.

---

## 7. CSRF Protection & API Token Isolation

1. **Web SSR:** `CSRFProtect(app)` enforces token validation across all state-mutating requests (`POST`, `PUT`, `DELETE`). HTML forms inject `{{ csrf_token() }}`.
2. **REST API Isolation:** The headless API Blueprint (`/api/v1/`) is explicitly exempted from CSRF enforcement via:
   ```python
   csrf.exempt(api_bp)
   app.register_blueprint(api_bp, url_prefix='/api/v1')
   ```
   The API relies entirely on cryptographically signed JWT Bearer tokens in the `Authorization` header, eliminating CSRF vulnerabilities by design.

---

## 8. Audit Logging (`AuditLog`)

Critical administrative actions (bracket resets, manual seed changes, score overrides) are permanently recorded in the `audit_logs` table:
* Captures: `user_id`, `action_type`, `target_id`, `target_name`, `reason`, `explanation`, and `details` (JSON before/after diffs).
* Enables forensic auditing in disputed championship matches.
