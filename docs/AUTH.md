# The Baseline Society — Authentication, Authorization & Security Architecture (AUTH.md)

**Document Status:** Approved  
**Source of Truth:** Inherits from [`FEATURES.md`](FEATURES.md), [`API.md`](API.md), and [`ARCHITECTURE.md`](ARCHITECTURE.md)  
**Security Standard:** OWASP Top 10 Compliant (ASVS 4.0 Level 2)  
**Authentication Handlers:** Flask-WTF (Web Sessions) & Flask-JWT-Extended (Headless API)  
**Revision:** Hardened (fail-closed RBAC, Court PIN v2, rate limiting)  
**Last Updated:** November 2026  

---

## 1. Dual Authentication Architecture

The Baseline Society enforces a dual authentication model tailored to its hybrid SSR and headless REST API structure:

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

The Baseline Society enforces a multi-tiered authorization model separating platform-wide system roles from tournament-scoped staff and temporary court umpires:

### 2.1 Platform System Roles (`users.role`)
1. **`superadmin`:** Platform administrators with global override authority across all tournaments, user accounts, audit trails, and database sync tools.
2. **`admin`:** Tournament organizers and academy directors authorized to create tournaments, configure categories, manage finances, and oversee operations.
3. **`user` / `player`:** Registered athletes, coaches, and team captains who self-register, manage player profiles, submit nominations, and compete.
4. **Guest (Unauthenticated Public):** Public spectators capable of browsing tournaments, viewing public brackets, tracking live scores, and downloading published Draw & Order of Play PDFs.

### 2.2 Tournament-Scoped Roles
Roles are ranked; a higher rank includes every lower-rank capability. The check is **fail-closed**: unknown roles never pass.

| Rank | Role | Stored in | Capability |
| :---: | :--- | :--- | :--- |
| 10 | `scorer` | `tournament_staff.role` | Match score reporting and live court updates |
| 20 | `official` | `tournament_staff.role` | Chief referee decisions: walkovers, retirements, disputes, score corrections |
| 30 | `manager` | `tournament_staff.role` | Courts, schedules, delays, check-in, seeds |
| 40 | `owner` | `tournaments.user_id` | Settings, finances, staff appointment, PIN generation, draw publication |
| 100 | `superadmin` | `users.role` | Global override; every mutating override is audit-logged |

**Legacy aliases:** older code and documents use `tournament_admin`, `desk`, and `umpire`. They map to `manager`, `manager`, and `scorer` respectively and must be migrated in `tournament_staff.role` with an Alembic data migration. Only the `owner` (or a superadmin) may appoint staff or generate PINs; delegated staff can never reach rank 40.

### 2.3 Temporary Court Access PINs (Court PIN v2)
Volunteer chair umpires can score on court tablets without an account. The PIN is a credential and is handled like one:

* **Format:** 6 digits, generated with `secrets.randbelow`, unique per tournament. Each PIN is a row in `tournament_staff` (`court_pin`, `pin_expires_at`, `assigned_court`).
* **Validity:** 8h, 24h, or 48h; expired PINs are rejected and purged. Organizers can revoke any PIN instantly.
* **Court binding:** a PIN session may score only matches whose `court_name` equals the PIN's `assigned_court` (or any court when the organizer explicitly creates an unbound PIN).
* **Storage:** only a keyed hash (`HMAC-SHA256` with a server secret) is stored; the plain PIN is shown once at creation. Comparison uses `hmac.compare_digest`.
* **Entry:** at `/tournaments/<slug>/court-pin` (the `/t/<slug>/score-login` path in earlier drafts is retired). The form requires the scorer's display name. After success the session is regenerated and stores `{staff_id, court, exp, display_name}` in `session['court_pin_auth_<tournament_id>']`.
* **Brute-force defense:** 5 failed attempts per IP and per tournament lock PIN entry for 15 minutes; failures are logged. This is mandatory because a 6-digit space is only 1,000,000 values.
* **Scope:** scoring endpoints only. PIN sessions cannot appoint staff, publish draws, export data, or use the REST API.

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
| Report Live Match Scores | ❌ | ❌ | ❌ | ✅ (assigned court only) | ✅ | ✅ | ✅ | ✅ |
| Override Score (Competitor in Match) | ❌ (Blocked) | ❌ (Blocked) | ❌ (Blocked) | ❌ (Blocked) | ❌ (Blocked) | ❌ (Blocked) | ❌ (Blocked) | ✅ |
| Elevate Platform User to Admin | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |

> **Note:** a superadmin can override a score only through an audited action that records a reason. Superadmin is never exempt from logging.

---

## 3. Concurrency & Integrity Defenses

### 3.1 Anti-Conflict of Interest Protection
To protect athletic integrity, playing competitors are strictly blocked from recording or altering scores for their own matches.

* Guard: `check_scoring_conflict_of_interest(match, user)` in [`app/web/controllers/auth.py`](app/web/controllers/auth.py). It **raises `403`**; it must never return a status tuple that a caller can ignore.
* It resolves every linked account through `Player.user_id` (participants have no `user_id` column): `participant.player`, `participant.player2` (doubles partner), all `team_members` of a team entry, every rubber lineup player (`p1_player1_id`, `p1_player2_id`, `p2_player1_id`, `p2_player2_id`), and the parent tie of a rubber.
* **Compensating controls for Court PIN sessions** (which have no user identity to compare): the scorer must enter a display name, the session is bound to one court, every action is audit-logged with the PIN session and IP, and the organizer should assign PIN holders who are not competing. Organizers see an audit view of PIN-scored matches.

```python
def check_scoring_conflict_of_interest(match, user):
    if user is None:                      # PIN session: handled by compensating controls
        return
    blocked = linked_user_ids(match)      # players, partners, team roster, rubber lineup, parent tie
    blocked.discard(None)
    if user.id in blocked:
        abort(403, "Conflict of interest: Active participants cannot officiate or score their own matches.")
```

### 3.2 Optimistic Concurrency Control (`lock_version`)
Simultaneous score reporting by desk coordinators and court umpires is guarded via optimistic locking:
* `Match.lock_version` increments with every score update. The reporting form and API **must** send the expected value; omitting it is a `400`.
* The comparison and the write happen in one atomic statement (or via SQLAlchemy `version_id_col`), so a check-then-write race is impossible:
  ```python
  updated = db.session.execute(
      update(Match)
      .where(Match.id == match.id, Match.lock_version == submitted_version)
      .values(score1=s1, score2=s2, status=new_status, lock_version=Match.lock_version + 1)
  ).rowcount
  if updated != 1:
      abort(409)
  ```
* On mismatch a **409 Conflict** is returned, preventing silent score overwrites.

### 3.3 Team Captain Lineup Nomination Window
- Guard function: `check_fixture_lineup_access(fixture, user)` in [`app/web/controllers/auth.py`](app/web/controllers/auth.py).
- Captains can only nominate players for their own squad (opposing team fields are strictly isolated).
- Lineups automatically lock **15 minutes** before `scheduled_time`, or as soon as the tie status becomes `in_progress`, whichever happens first.

### 3.4 Multi-Tenant Academy Isolation
- Guard function: `check_academy_access(academy, require_admin=False)` in [`app/web/controllers/auth.py`](app/web/controllers/auth.py).
- Ensures academy announcements and member rosters can only be modified by approved academy administrators or superadmins.

---

## 4. Broken Object Level Authorization (BOLA/IDOR) Defense

A critical security vulnerability in multi-tenant tournament software is BOLA (Broken Object Level Authorization), where an authenticated organizer attempts to alter fixtures or settings belonging to another organizer by manipulating IDs in the URL.

The Baseline Society neutralizes BOLA at both the controller and API layers:

### 4.1 Central Guard (`check_tournament_access`)
Defined in [`app/web/controllers/auth.py`](app/web/controllers/auth.py). It is used by web controllers **and** the API, and takes the user explicitly because JWT identities are not visible to Flask-Login:

```python
ROLE_RANK = {"scorer": 10, "official": 20, "manager": 30, "owner": 40}
LEGACY_ALIASES = {"umpire": "scorer", "desk": "manager", "tournament_admin": "manager"}  # remove after data migration

def check_tournament_access(tournament, min_role="scorer", user=None, court=None):
    required = ROLE_RANK.get(min_role)
    if required is None:
        raise ValueError(f"Unknown min_role {min_role!r}")      # programming error, never silently allow
    user = user or (current_user if current_user.is_authenticated else None)
    if user is not None:
        if user.role == "deleted":
            abort(401)
        if user.role == "superadmin":
            audit_superadmin_override(user, tournament)          # logged on mutating requests
            return "superadmin"
        if tournament.user_id == user.id:
            return "owner"
        staff = db.session.scalar(select(TournamentStaff).where(
            TournamentStaff.tournament_id == tournament.id, TournamentStaff.user_id == user.id))
        if staff:
            role = LEGACY_ALIASES.get(staff.role, staff.role)
            if ROLE_RANK.get(role, 0) >= required:             # unknown staff role = rank 0 = denied
                return role
    pin = session.get(f"court_pin_auth_{tournament.id}")         # web only; never accepted by the API
    if pin and min_role == "scorer" and pin_session_valid(pin, court):
        return "court_pin"
    abort(403)
```

Defects in earlier drafts that this version removes: (1) unknown `min_role` values defaulted to rank 0 and let any staff row through; (2) the ranking table used role names that did not match the database enum; (3) a delegated `tournament_admin` satisfied `min_role="owner"` and could appoint more staff; (4) PIN sessions were not court-bound or expiring.

Every mutation route in `tournament_bp` and `category_bp` calls this guard before changing state. Read routes for private data (`is_private`, draft draws, rosters, exports) call it as well.

### 4.2 API Layer Defense
Defined in [`app/api/matches.py`](app/api/matches.py):
```python
@api_bp.route('/matches/<int:match_id>/report', methods=['POST'])
@jwt_required()
def report_match(match_id):
    user = db.session.get(User, int(get_jwt_identity()))
    if user is None or user.role == 'deleted':
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    match = db.session.get(Match, match_id) or abort(404)
    check_tournament_access(match.tournament, min_role="scorer", user=user)
    check_scoring_conflict_of_interest(match, user)
```

---

## 5. Cryptographic Standards & Password Security

* **Password hashing:** `generate_password_hash(password, method="scrypt")` (Werkzeug 3.x default). Older PBKDF2-HMAC-SHA256 hashes remain verifiable; on a successful login with a legacy hash the password is transparently re-hashed. The column `users.password_hash VARCHAR(256)` is large enough for both formats. Earlier drafts that stated "PBKDF2 with 260,000 iterations" were inaccurate.
  ```python
  def set_password(self, password):
      from werkzeug.security import generate_password_hash
      self.password_hash = generate_password_hash(password, method="scrypt")
  ```
* **Password policy:** 10 to 128 characters, common-password denylist, no composition rules that encourage predictable substitutions. The 128-character cap prevents hashing-based denial of service.
* **Verification:** constant-time `check_password_hash`; the same generic error and similar response time for unknown users and wrong passwords.
* **Secrets:** `SECRET_KEY` (sessions/CSRF), `JWT_SECRET_KEY` (API tokens), and the PIN-hash key are three separate random values of at least 32 bytes. None may use a documented default in production, and each must be rotatable.
* **Session cookies:** `SESSION_COOKIE_HTTPONLY=True`, `SESSION_COOKIE_SAMESITE='Lax'`, and `SESSION_COOKIE_SECURE=True` whenever `APP_ENV=production` (not merely "when running over HTTPS"). Sessions expire after 8 hours of inactivity for organizers; the session is regenerated on login, logout, and PIN authentication to prevent fixation.
* **Redirects:** the post-login `next` parameter must be a relative path on the same host; anything else is ignored (prevents open redirect).
* **Security headers (Flask-Talisman or equivalent):** `Strict-Transport-Security: max-age=31536000; includeSubDomains`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy` limited to needed features, `frame-ancestors 'none'`, and a Content-Security-Policy with `default-src 'self'` (fonts and scripts self-hosted; inline scripts use nonces).
* **Reverse proxy:** behind Gunicorn/nginx or Vercel the app must use `ProxyFix` so client IPs (for rate limiting and audit logs) and the HTTPS scheme (for secure cookies) are correct.

---

## 6. Superadmin Bootstrapping

Fresh deployments need an administrator without interactive shell access, but default credentials must never reach production:

* Implemented in `bootstrap_superadmin()` in [`app/web/controllers/auth.py`](app/web/controllers/auth.py).
* It runs only when **no user with `role='superadmin'` exists** (not merely when the users table is empty).
* **Production:** `SUPERADMIN_USERNAME` and `SUPERADMIN_PASSWORD` are mandatory, the password must be at least 12 characters and must not equal the documented development default. Otherwise startup fails with a clear error.
* **Development:** if variables are omitted, the defaults (`superadmin` / `adminpassword`) are allowed only when `APP_ENV` is not `production`, and a warning is logged.
* **Concurrency:** on serverless platforms several cold starts can run at once. Run bootstrap from the deployment pipeline (`scripts/init_uat_db.py` or a `flask` CLI command), or wrap it in a transaction and catch `IntegrityError` so only one superadmin is created.
* The password is never logged. After first login it should be changed and the environment variable removed from the platform.

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

Critical actions are permanently recorded in `audit_logs`:
* **Always logged:** bracket resets, manual seed changes, **every score completion, correction, and reset**, draw publish/unpublish, staff appointment/revocation, PIN creation/revocation, superadmin overrides, role changes, payment approvals, and repeated failed logins/PIN attempts.
* **Fields:** `user_id`, `action_type`, `target_id`, `target_name`, `reason`, `explanation`, and `details` (JSON before/after diff).
* **PIN and anonymous actors:** PIN sessions have no user, so `audit_logs.user_id` must be nullable and a `staff_id` / `actor_label` (scorer display name) plus IP are recorded instead (see [`DATABASE.md`](DATABASE.md) §4).
* Audit rows are append-only; the application database role has no `UPDATE`/`DELETE` privilege on `audit_logs`.

---

## 9. Rate Limiting & Brute-Force Protection

Use Flask-Limiter with shared storage (Redis or the database); in-memory limits do not work across workers or serverless instances.

| Surface | Limit | Response |
| :--- | :--- | :--- |
| Web login / `POST /api/v1/auth/login` | 10 / 15 min per IP + username; progressive lockout | 429 + generic error |
| Registration | 5 / hour per IP | 429 |
| Court PIN entry | 5 failures / 15 min per IP and tournament | 15-minute lock |
| Guest registration submit | 10 / hour per IP | 429 |
| Public live feed | 30 / min per IP (CDN-cached) | 304 / 429 |
| Password reset / email verification (when added) | 5 / hour per account | 429 |

## 10. Guest Registration & Account Claiming Security

* Guest registrations are stored against the internal `anonymous_registrations` user. That account **must not be loginable** (random unusable hash, role excluded from login), and it must never be shown or addressable as a normal user.
* Reusing an existing `Player` profile by matching email or mobile must **not** expose that profile's data to the guest. The guest sees only what they typed; matching happens server-side.
* **Account claiming requires proof of control:** a player profile is linked to a new `User` only after the email is verified (verification link) or the mobile number is verified (OTP). Matching on unverified claimed email/phone alone would let anyone hijack another athlete's history and personal data.
* UPI transaction references must be unique per tournament and format-validated; organizers approve payments manually, and approvals are audit-logged.

## 11. Uploads & Document Export Security

* **Uploads (avatars, match attachments):** allow-list JPEG/PNG/WebP (and PDF for scoresheets), maximum 5 MB, server-generated random filenames, content sniffing plus re-encoding for images, never serve from a path derived from user input, never store under `app/web/static/`. On Vercel the filesystem is read-only, so use object storage (for example Supabase Storage) with private buckets and short-lived signed URLs. SVG/HTML uploads are forbidden.
* **PDF export:** all user-supplied text (names, notes) is HTML-escaped before it enters an `xhtml2pdf` template, and the renderer's link callback resolves only local, allow-listed assets (no remote URLs), preventing HTML injection and server-side request forgery.
* **Excel/CSV:** exports neutralize formula cells (`=`, `+`, `-`, `@`); imports enforce size, row, and column limits and are parsed in read-only mode.

## 12. Privacy & Data Protection

The Baseline Society stores personal data of athletes, including minors (age categories U10 to U18), plus date of birth, contact details, address, and blood group.
* Collect only what a tournament needs; hide `address`, `blood_group`, `dob`, `email`, and `contact_number` from every public page and API response.
* Public player portfolios show name, avatar, statistics, and results only.
* Obtain and record consent at registration; for under-18 participants obtain guardian consent. India's Digital Personal Data Protection Act, 2023 imposes verifiable-consent and children's-data duties, so have counsel confirm the exact obligations before launch.
* Provide data export and deletion: deleting a user sets `role='deleted'`, blanks personal fields, and anonymizes historical player records while preserving match results.
* Define retention (for example, delete unverified guest contact data after the tournament plus a fixed period).

## 13. Security Regression Tests (required)

Add tests to `tests/test_rbac.py` and `tests/test_security.py` covering at least: unknown `min_role` raises; unknown staff role is denied; delegated manager cannot appoint staff; PIN session cannot score another court or after expiry; five wrong PINs lock entry; omitting `lock_version` returns 400 and a stale one 409; draft-draw data absent from public API and live feed; public schemas exclude private fields; player, doubles partner, rubber-lineup player, and team member cannot score their own match; production start fails with default secrets; formula-injection cells are escaped in exports.
