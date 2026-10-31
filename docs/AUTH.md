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

## 2. Role-Based Access Control (RBAC)

TourneyPro categorizes users into four hierarchical roles:

1. **`superadmin`:** Platform administrators with global override authority across all tournaments, user accounts, and database sync tools.
2. **`admin`:** Tournament organizers and academy directors authorized to manage their own tournaments, categories, drafts, court schedules, and match results.
3. **`user` / `player`:** Registered athletes and fans who can self-register, manage their player portfolio, view brackets, and follow live scores.
4. **Guest (Unauthenticated Public):** Public spectators capable of browsing tournaments, viewing public brackets, tracking live scores, and submitting guest registrations.

### 2.1 Permissions Matrix

| Operational Capability | Guest | User / Player | Admin (Owner) | Admin (Non-Owner) | Superadmin |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Browse Tournaments & Live Scores | ✅ | ✅ | ✅ | ✅ | ✅ |
| Submit Tournament Registration | ✅ (Guest) | ✅ | ✅ | ✅ | ✅ |
| Create New Tournament | ❌ | ❌ | ✅ | ✅ | ✅ |
| Modify Tournament Settings / Dates | ❌ | ❌ | ✅ | ❌ (403) | ✅ |
| Generate / Reset Brackets | ❌ | ❌ | ✅ | ❌ (403) | ✅ |
| Run Team Draft Wizard (Mode A & B) | ❌ | ❌ | ✅ | ❌ (403) | ✅ |
| Record Live Scores & Advance Winners | ❌ | ❌ | ✅ | ❌ (403) | ✅ |
| Export Draws & Order of Play PDF | ❌ | ❌ | ✅ | ❌ (403) | ✅ |
| Elevate User to Admin Role | ❌ | ❌ | ❌ | ❌ | ✅ |
| Trigger Database Schema Sync | ❌ | ❌ | ❌ | ❌ | ✅ |

---

## 3. Broken Object Level Authorization (BOLA/IDOR) Defense

A critical security vulnerability in multi-tenant tournament software is BOLA (Broken Object Level Authorization), where an authenticated organizer attempts to alter fixtures or settings belonging to another organizer by manipulating IDs in the URL.

TourneyPro completely neutralizes BOLA at both the controller and API layers:

### 3.1 Web Controller Defense (`check_tournament_ownership`)
Defined in [`app/web/controllers/auth.py`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/app/web/controllers/auth.py):
```python
def check_tournament_ownership(tournament):
    user = get_current_user()
    if not user:
        abort(401)
    if user.role != 'superadmin' and tournament.user_id != user.id:
        abort(403)
```
Every mutation route in `tournament_bp` and `category_bp` calls this guard prior to executing any state alteration.

### 3.2 API Layer Defense
Defined in [`app/api/matches.py`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/app/api/matches.py):
```python
@api_bp.route('/matches/<int:match_id>/report', methods=['POST'])
@jwt_required()
def report_match(match_id):
    current_user_id = int(get_jwt_identity())
    user = User.query.get(current_user_id)
    match = Match.query.get_or_404(match_id)
    
    # Strict BOLA ownership guard:
    if user.role != 'superadmin' and match.tournament.user_id != user.id:
        return jsonify({"success": False, "message": "Forbidden: You do not own this tournament"}), 403
```

---

## 4. Cryptographic Standards & Password Security

* **Password Hashing:** Passwords are hashed using Werkzeug's `generate_password_hash` implementation of **PBKDF2-HMAC-SHA256** with salt length of 16 bytes and 260,000 iterations:
  ```python
  def set_password(self, password):
      from werkzeug.security import generate_password_hash
      self.password_hash = generate_password_hash(password)
  ```
* **Password Verification:** Constant-time comparison via `check_password_hash` prevents timing attacks.
* **Session Cryptography:** Flask session cookies are signed using `SECRET_KEY` with `HttpOnly=True`, `SameSite='Lax'`, and secure flag when running over HTTPS.

---

## 5. Superadmin Bootstrapping

On fresh deployments or container starts, the application automatically ensures an administrative user exists without requiring interactive shell access:

* Implemented in `bootstrap_superadmin()` in [`app/web/controllers/auth.py`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/app/web/controllers/auth.py).
* Checks if `User.query.count() == 0`.
* If empty, provisions the superadmin using environment variables:
  * `SUPERADMIN_USERNAME` (Default: `superadmin`)
  * `SUPERADMIN_PASSWORD` (Default: `adminpassword`)
* Sets user `role = 'superadmin'`.

---

## 6. CSRF Protection & API Token Isolation

1. **Web SSR:** `CSRFProtect(app)` enforces token validation across all state-mutating requests (`POST`, `PUT`, `DELETE`). HTML forms inject `{{ csrf_token() }}`.
2. **REST API Isolation:** The headless API Blueprint (`/api/v1/`) is explicitly exempted from CSRF enforcement via:
   ```python
   csrf.exempt(api_bp)
   app.register_blueprint(api_bp, url_prefix='/api/v1')
   ```
   The API relies entirely on cryptographically signed JWT Bearer tokens in the `Authorization` header, eliminating CSRF vulnerabilities by design.

---

## 7. Audit Logging (`AuditLog`)

Critical administrative actions (bracket resets, manual seed changes, score overrides) are permanently recorded in the `audit_logs` table:
* Captures: `user_id`, `action_type`, `target_id`, `target_name`, `reason`, `explanation`, and `details` (JSON before/after diffs).
* Enables forensic auditing in disputed championship matches.
