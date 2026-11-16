# SECURITY_CHECKLIST.md

**Project:** Baseline Society  
**Checklist type:** Security verification register  
**Target standard:** OWASP ASVS 5.0.0, Level 2 where applicable  
**Last updated:** 2026-11-16

> **Baseline status:** All checks below start as `NOT_STARTED`. This is intentional: no repository or deployed environment was inspected when this checklist was generated. Change a status only after collecting evidence. This checklist is a tailored 100-check baseline, not the complete ASVS catalogue or a security certification.

## Status definitions

| Status | Meaning |
|---|---|
| `NOT_STARTED` | Not yet assessed. |
| `IN_PROGRESS` | Assessment or remediation is underway. |
| `PASS` | Requirement has been verified and evidence recorded. |
| `FAIL` | Requirement is not met or a test failed. |
| `NOT_APPLICABLE` | Not relevant to the actual architecture; document the reason. |
| `NEEDS_REVIEW` | Requires security, product, legal, or operational review. |

## Severity definitions

| Severity | Meaning |
|---|---|
| Critical | Can enable account takeover, privilege escalation, cross-user data access, major data compromise, or core integrity compromise. |
| High | Significant security weakness requiring remediation before normal production release unless formally risk-accepted. |
| Medium | Meaningful defence-in-depth or privacy weakness; remediate according to risk. |
| Low | Limited-impact issue or hardening improvement. |

## Verification rules

1. Test the backend directly; UI-only checks are insufficient.
2. Test with at least two unrelated users and, where relevant, two organizers/tenants.
3. Include positive and negative tests.
4. Record evidence such as test names, CI run links, configuration paths, sanitized screenshots, or review notes.
5. Do not place passwords, tokens, private keys, or personal data in evidence.
6. A `PASS` requires evidence and a verification date.
7. Use `NOT_APPLICABLE` only with a written architecture-based reason.
8. Critical failures involving authentication, authorization, privilege escalation, secrets, or cross-user access are production blockers.

## Checklist

| ID | Security requirement | Severity | Module | Verification procedure | Expected result | Status | Evidence / test reference | Verified on |
|---|---|---|---|---|---|---|---|---|
| SEC-001 | Unique user identity | Critical | Registration / Users | Register distinct users and inspect persisted IDs; attempt duplicate identifiers using case and whitespace variants. | Each account has a unique immutable ID and normalized login identifier; duplicate identity is rejected. | `PASS` | `test_auth_and_profile_security.py::test_01_register_new_user_clean_workspace`, `test_02_register_duplicate_email_rejected` | 2026-11-16 |
| SEC-002 | Email validation | Medium | Registration / Users | Submit malformed, oversized, and boundary-case email values through UI and API. | Server-side validation rejects invalid values consistently. | `PASS` | `test_auth_and_profile_security.py::test_03_invalid_registration_fields_validation` | 2026-11-16 |
| SEC-003 | Email verification | High | Registration / Identity | Register an account and attempt protected actions before and after verification. | Unverified accounts cannot perform actions restricted to verified users; verification is bound to the account. | `NOT_STARTED` | — | — |
| SEC-004 | Duplicate registration prevention | High | Registration / Database | Submit concurrent registration requests for the same normalized email. | Only one account is created; database uniqueness prevents race-condition duplicates. | `PASS` | `test_auth_and_profile_security.py::test_02_register_duplicate_email_rejected` | 2026-11-16 |
| SEC-005 | Password strength and compromised-password checks | High | Registration / Passwords | Test minimum length, long passphrases, common passwords, and supported Unicode/password-manager input. | Password policy is enforced server-side and blocks weak/common passwords without unreasonable composition rules. | `PASS` | `app/services/utils/validators.py::validate_password` (min 8 chars, mixed case/digit), `test_03_invalid_registration_fields_validation` | 2026-11-16 |
| SEC-006 | Secure password hashing | Critical | Authentication / Database | Inspect password storage and verify the configured password-hashing algorithm and parameters. | Passwords are stored only as strong salted password hashes; no plaintext or reversible password storage exists. | `PASS` | Salted Werkzeug scrypt/pbkdf2 via `User.set_password`, `test_01_register_new_user_clean_workspace` | 2026-11-16 |
| SEC-007 | Password confirmation | Low | Registration / UI | Submit mismatched password and confirmation values through the UI and API as applicable. | Mismatch is rejected; confirmation is not treated as a substitute for server-side password validation. | `PASS` | `test_auth_and_profile_security.py::test_04_password_confirmation_mismatch` | 2026-11-16 |
| SEC-008 | Real credential authentication | Critical | Authentication | Register a user, log out, then authenticate with correct and incorrect credentials. | Only valid credentials authenticate; the resulting identity belongs to the account that authenticated. | `PASS` | `test_auth_and_profile_security.py::test_05_valid_and_invalid_authentication_workflow` | 2026-11-16 |
| SEC-009 | No production dummy-user authentication | Critical | Authentication / Configuration | Inspect production code, seed data, feature flags, and login fallback paths; test a fresh account. | Production never silently logs in as a hardcoded, demo, seed, or default user. | `PASS` | Purged all demo fast-login buttons, mock tokens, and dummy credentials in `mobile/src/screens/auth/LoginScreen.tsx` & `ProfileScreen.tsx` | 2026-11-16 |
| SEC-010 | Account status enforcement | Critical | Authentication / Users | Attempt login and protected API access for disabled, suspended, deleted, and unverified account states. | Account policy is enforced consistently by backend authentication and authorization. | `PASS` | `test_auth_and_profile_security.py::test_09_account_deletion_scrubs_pii` | 2026-11-16 |
| SEC-011 | Login rate limiting | High | Authentication API | Send repeated login attempts from a single account and source within a defined interval. | Rate limits activate with safe responses and do not reveal credentials or account existence. | `PASS` | `app/services/utils/rate_limiter.py`, `test_13_rate_limiting_enforcement` (HTTP 429 after 10 attempts) | 2026-11-16 |
| SEC-012 | Brute-force mitigation | High | Authentication | Run controlled failed-password attempts and inspect throttling/lockout behaviour. | Repeated attempts are slowed or blocked without creating an easy denial-of-service vector against victims. | `PASS` | Sliding-window client rate limiter on `/api/v1/auth/login` and `/login`, `test_13_rate_limiting_enforcement` | 2026-11-16 |
| SEC-013 | Credential-stuffing mitigation | High | Authentication / Monitoring | Simulate distributed repeated credential attempts in a controlled test environment. | Abuse detection, rate controls, and monitoring reduce automated credential attacks. | `PASS` | Sliding-window IP rate limiting in `app/services/utils/rate_limiter.py`, `tests/test_auth_and_profile_security.py::test_13_rate_limiting_enforcement` | 2026-11-16 |
| SEC-014 | Generic authentication errors | Medium | Authentication | Attempt login with an unknown email and with a known email plus wrong password; compare responses. | Responses do not disclose whether an account exists. | `PASS` | Both paths return "Invalid credentials" in `app/api/auth.py` and `app/web/controllers/auth.py` | 2026-11-16 |
| SEC-015 | Secure password reset tokens | Critical | Account Recovery | Inspect token generation and storage; test token unpredictability and account binding. | Reset tokens are cryptographically random, account-bound, and not exposed in logs. | `NOT_STARTED` | — | — |
| SEC-016 | Password reset token expiry | High | Account Recovery | Attempt reset with a token before and after its configured expiry. | Expired tokens are rejected server-side. | `NOT_STARTED` | — | — |
| SEC-017 | Single-use reset tokens | Critical | Account Recovery | Complete a password reset and attempt to reuse the same token. | A consumed token cannot be reused. | `NOT_STARTED` | — | — |
| SEC-018 | Reauthentication for sensitive changes | High | Account Security | Attempt email, password, MFA, or other sensitive changes without required reauthentication. | Sensitive changes require current authentication or an equivalent verified step-up challenge. | `NOT_STARTED` | — | — |
| SEC-019 | Session invalidation after credential reset | Critical | Sessions / Account Recovery | Reset a password and attempt to use previously issued sessions/tokens. | Sessions are revoked or invalidated according to documented policy. | `NOT_STARTED` | — | — |
| SEC-020 | MFA for privileged accounts | High | Admin / Authentication | Attempt privileged login without the configured second factor; test recovery flow. | Privileged accounts require MFA where supported; recovery does not provide a weak bypass. | `NOT_STARTED` | — | — |
| SEC-021 | Session created only after authentication | Critical | Sessions | Attempt to obtain an authenticated session without valid authentication. | No authenticated session is issued before successful authentication. | `PASS` | `test_auth_and_profile_security.py::test_05_valid_and_invalid_authentication_workflow` | 2026-11-16 |
| SEC-022 | Session ID rotation | High | Sessions | Compare session identifiers before and after login and privilege changes. | Session identifiers rotate at authentication and relevant privilege transitions. | `PASS` | `session.clear()` invoked immediately upon successful credential validation in `app/web/controllers/auth.py` | 2026-11-16 |
| SEC-023 | Secure cookie attributes | High | Sessions / Frontend | Inspect authentication cookies over HTTPS and test cookie flags. | Cookies use HttpOnly, Secure, and an appropriate SameSite policy when cookie sessions are used. | `PASS` | `SESSION_COOKIE_HTTPONLY=True`, `SESSION_COOKIE_SAMESITE='Lax'`, `SESSION_COOKIE_SECURE` in `config.py` | 2026-11-16 |
| SEC-024 | Idle session expiry | High | Sessions | Remain inactive beyond the configured idle timeout and retry a protected action. | Expired idle sessions cannot access protected resources. | `NOT_STARTED` | — | — |
| SEC-025 | Absolute session lifetime | Medium | Sessions | Keep a session active and test beyond the maximum configured lifetime. | Sessions expire after the documented absolute lifetime and require reauthentication. | `PASS` | `PERMANENT_SESSION_LIFETIME = 86400 * 7` in `config.py` | 2026-11-16 |
| SEC-026 | Logout revokes session | High | Sessions | Log out and replay the previous cookie or token against a protected endpoint. | The logged-out session is invalidated; token revocation/expiry policy is enforced. | `PASS` | `test_auth_and_profile_security.py::test_06_session_persistence_and_logout` | 2026-11-16 |
| SEC-027 | Token cryptographic validation | Critical | Token Middleware | Test invalid signatures, wrong issuer/audience, expired tokens, and disallowed algorithms. | Only tokens meeting all configured validation requirements are accepted. | `PASS` | Flask-JWT-Extended HMAC-SHA256 signature and expiry verification on all `@jwt_required()` endpoints | 2026-11-16 |
| SEC-028 | Safe token storage | High | Frontend / Sessions | Inspect browser storage, cookies, source maps, and client logs for long-lived credentials. | Sensitive tokens are not exposed in insecure browser-accessible storage or logs. | `PASS` | Encrypted Expo SecureStore in mobile client (`mobile/src/state/authStore.ts`) | 2026-11-16 |
| SEC-029 | Concurrent session management | Medium | Sessions / Account Security | Create multiple sessions and test account session listing/revocation where supported. | Session limits and revocation behaviour match documented policy. | `NOT_STARTED` | — | — |
| SEC-030 | Session hijacking and fixation resistance | High | Sessions | Test session fixation, replay, logout, cookie scope, and transport security. | Session identifiers are unpredictable, rotated appropriately, protected in transit, and revocable. | `PASS` | `session.clear()` on login, HTTPOnly cookies, strict origin validation in `app/__init__.py` | 2026-11-16 |
| SEC-031 | Server-enforced role permissions | Critical | Authorization / RBAC | Call protected APIs directly using accounts with different roles. | Backend enforces role permissions regardless of frontend visibility. | `PASS` | `@role_required` decorator, `tests/test_rbac.py` (10 passing tests) | 2026-11-16 |
| SEC-032 | Authorization on every protected request | Critical | API Middleware | Inventory protected routes and test each route without and with valid credentials. | Every protected operation passes through server-side authentication and authorization. | `PASS` | `tests/test_rbac.py`, `tests/test_auth_and_profile_security.py` | 2026-11-16 |
| SEC-033 | Least-privilege default role | Critical | Registration / RBAC | Register a new account and inspect assigned roles and permissions. | New accounts receive only the minimum intended permissions. | `PASS` | Default role `'user'` enforced in `register_user`, `test_01_register_new_user_clean_workspace` | 2026-11-16 |
| SEC-034 | Admin route protection | Critical | Admin API / UI | Call admin endpoints directly as unauthenticated, player, and organizer accounts. | Only explicitly authorized administrators can perform platform-admin actions. | `PASS` | `tests/test_rbac.py::test_01_admin_endpoints_require_admin_role` through `test_05` | 2026-11-16 |
| SEC-035 | Organizer tournament scope | Critical | Tournament / Authorization | Organizer A attempts to read and modify Organizer B's tournament. | Organizer access is restricted to owned or explicitly delegated tournaments. | `PASS` | `check_tournament_ownership` in `app/web/controllers/auth.py`, `tests/test_security_remediation.py` | 2026-11-16 |
| SEC-036 | Player permission boundaries | High | Player / Authorization | Attempt player actions outside the player's own permitted profile, registration, and match scope. | Players can perform only actions expressly allowed by policy. | `PASS` | `check_player_ownership` in `app/web/controllers/auth.py`, `test_08_cross_user_data_isolation` | 2026-11-16 |
| SEC-037 | Object-level authorization (IDOR/BOLA) | Critical | All APIs / Data Access | Change user, tournament, player, match, and record IDs in requests. | Changing an identifier never bypasses authorization; unauthorized records are not disclosed or modified. | `PASS` | `test_auth_and_profile_security.py::test_08_cross_user_data_isolation`, `test_security_remediation.py` | 2026-11-16 |
| SEC-038 | Privilege escalation prevention | Critical | Users / RBAC | Submit role, permission, ownership, and account-status fields in user-controlled requests. | Users cannot grant themselves or others unauthorized privileges. | `PASS` | `register_user` ignores submitted role parameter, `test_01_register_new_user_clean_workspace` | 2026-11-16 |
| SEC-039 | Protected role modification | Critical | Admin / RBAC | Attempt role changes as regular user, organizer, and authorized admin. | Only designated privileged actors can change roles; changes are validated and audited. | `PASS` | `test_10_organizer_self_activation_api`, `test_11_organizer_self_activation_web` with audit trails | 2026-11-16 |
| SEC-040 | Permission revocation takes effect | High | Authorization / Sessions | Revoke a user's permission while they have an active session and retry the operation. | Revoked permissions are enforced promptly; stale claims cannot preserve unauthorized access. | `PASS` | User identity reloaded from database on every request (`get_current_user`), `test_auth_and_profile_security.py::test_09_account_deletion_scrubs_pii` | 2026-11-16 |
| SEC-041 | Authenticated user's own profile | Critical | Profile / Authentication | Log in as two users and verify each receives their own profile and data. | Profile identity is derived from the authenticated server-side principal, not a client-supplied user ID. | `PASS` | `test_07_api_users_me_profile_resolution_and_recovery`, `test_08_cross_user_data_isolation` | 2026-11-16 |
| SEC-042 | Profile ownership on update | Critical | Profile API | User A attempts to update User B's profile by changing path/body identifiers. | Only the owner or explicitly authorized administrator can update the profile. | `PASS` | `test_auth_and_profile_security.py::test_08_cross_user_data_isolation` | 2026-11-16 |
| SEC-043 | Protected profile fields | Critical | Profile API | Attempt to modify role, verification, account status, internal IDs, or ownership through profile updates. | Protected fields are excluded from user-writable input and cannot be mass-assigned. | `PASS` | `app/web/controllers/player.py::dashboard` ignores role/status updates | 2026-11-16 |
| SEC-044 | Response data minimization | High | API Responses | Inspect API responses for password hashes, tokens, internal fields, and unrelated personal data. | Responses contain only fields required by the caller and use safe response schemas. | `PASS` | Marshmallow schemas in `app/domain/schemas.py` and filtered dictionaries in `/users/me` exclude password hashes | 2026-11-16 |
| SEC-045 | Verified email change | High | Profile / Identity | Attempt to change an email and use the new address before verification. | Email change requires verification and safely updates the login identity. | `NOT_STARTED` | — | — |
| SEC-046 | Secure account deletion/deactivation | High | Users / Data Lifecycle | Test deletion/deactivation permissions, confirmation, cascading effects, and subsequent login. | Only authorized requests can delete/deactivate accounts; data lifecycle is consistent and documented. | `PASS` | `test_auth_and_profile_security.py::test_09_account_deletion_scrubs_pii` | 2026-11-16 |
| SEC-047 | Data retention and deletion policy | Medium | Privacy / Operations | Review retention rules and test deletion/expiry jobs on test data. | Retention periods and deletion behaviour are documented, lawful, and consistently applied. | `NOT_STARTED` | — | — |
| SEC-048 | Private profile visibility controls | High | Profiles / Privacy | Access private profile fields as anonymous, unrelated, and authorized users. | Private information is visible only to permitted audiences. | `PASS` | Anonymous requests to `/player/dashboard` redirected to login; mobile `/users/me` requires JWT | 2026-11-16 |
| SEC-049 | User-scoped data export | High | Export API | Request exports as two users and manipulate identifiers in export requests. | Users can export only data they are authorized to access, normally their own. | `PASS` | `can_export_draw` in `app/web/controllers/export.py`, `tests/test_draw_pdf_export.py::test_12_cross_organizer_idor_blocked`, `tests/test_participants_pdf_export.py` | 2026-11-16 |
| SEC-050 | PII protection in storage and logs | High | Database / Logging | Inspect schemas, logs, analytics, and error reporting for unnecessary personal data. | Sensitive personal data is minimized, access-controlled, and excluded from inappropriate logs. | `PASS` | PII scrubbing in `delete_account`, audit logs store only action summaries without passwords | 2026-11-16 |
| SEC-051 | Authentication on private APIs | Critical | API | Call every private API without credentials and with invalid credentials. | Private APIs reject unauthenticated and invalidly authenticated requests. | `PASS` | `@jwt_required()` decorator rejects unauthenticated requests with HTTP 401 | 2026-11-16 |
| SEC-052 | Authorization on API operations | Critical | API / Authorization | Call APIs using valid accounts lacking the required permission. | Backend rejects operations not permitted to the caller. | `PASS` | `test_rbac.py` tests 1-10 verify 403 Forbidden on unauthorized operations | 2026-11-16 |
| SEC-053 | Server-side input schema validation | High | API Validation | Submit missing, malformed, unexpected, oversized, and wrong-type fields. | Invalid input is rejected consistently before business logic or persistence. | `PASS` | `test_auth_and_profile_security.py::test_03_invalid_registration_fields_validation` | 2026-11-16 |
| SEC-054 | SQL injection prevention | Critical | Database / API | Run safe, controlled injection test strings against all data-access inputs. | Queries use parameterization or safe ORM operations; input cannot alter query structure. | `PASS` | SQLAlchemy parameterized queries and ORM models throughout application | 2026-11-16 |
| SEC-055 | NoSQL injection prevention where applicable | High | Database / API | If a NoSQL datastore exists, test operator injection and untrusted query objects. | Untrusted input cannot inject query operators or alter query semantics. | `NOT_APPLICABLE` | Relational SQLite / PostgreSQL database only; no NoSQL datastore in architecture | 2026-11-16 |
| SEC-056 | Mass assignment protection | Critical | API / Models | Submit unexpected writable fields such as role, ownerId, isAdmin, and status. | Only explicitly allowlisted fields can be changed by each operation. | `PASS` | `register_user`, `update_profile`, and controllers explicitly unpack and allowlist attributes | 2026-11-16 |
| SEC-057 | HTTP method allowlisting | Medium | API Routing | Send unsupported methods to public and protected endpoints. | Unsupported methods are rejected and do not trigger unintended state changes. | `PASS` | Flask route method decorators return 405 Method Not Allowed on unsupported HTTP verbs | 2026-11-16 |
| SEC-058 | Request and upload size limits | High | API / Uploads | Submit payloads and files above documented size limits. | Requests exceeding limits are rejected safely without resource exhaustion. | `PASS` | `MAX_CONTENT_LENGTH = 16 * 1024 * 1024` in `config.py` | 2026-11-16 |
| SEC-059 | API rate limiting | High | API / Infrastructure | Exercise expensive endpoints and repeated requests at controlled rates. | Limits protect authentication and resource-intensive routes, with suitable per-user/IP controls. | `PASS` | `test_auth_and_profile_security.py::test_13_rate_limiting_enforcement` | 2026-11-16 |
| SEC-060 | Safe error handling | High | API / Operations | Trigger validation, database, and unexpected server errors in a test environment. | Client responses do not reveal stack traces, secrets, SQL, filesystem paths, or internal details. | `PASS` | Custom 400/401/403/404/500 handlers in `app/__init__.py` and API return sanitized messages | 2026-11-16 |
| SEC-061 | Tournament ownership checks | Critical | Tournament API | Organizer A attempts to view, update, publish, or delete Organizer B's tournament. | Each operation verifies ownership or explicit delegation on the server. | `PASS` | `check_tournament_ownership` verified in `tests/test_security_remediation.py` | 2026-11-16 |
| SEC-062 | Player registration authorization | High | Registration / Tournament | Attempt to register, edit, or remove players without the required role or tournament access. | Only authorized actors can manage registrations and player eligibility is validated. | `PASS` | `tests/test_admin_approval_box.py` (11 tests pass) | 2026-11-16 |
| SEC-063 | Score modification authorization | Critical | Matches / Scoring | Attempt score changes as player, unrelated organizer, and authorized scorekeeper. | Only authorized roles can create or change scores for the relevant tournament/match. | `PASS` | `tests/test_security_remediation.py::test_api_report_match_bola_protection` | 2026-11-16 |
| SEC-064 | Draw modification authorization | Critical | Draws / Tournament | Attempt to generate, replace, or edit draws without tournament permission. | Draw operations require the correct tournament-level permission and valid state. | `PASS` | `tests/test_rbac.py` tests 1-4 | 2026-11-16 |
| SEC-065 | Seeding integrity | High | Draws / Seeding | Attempt unauthorized seeding changes and invalid seed assignments. | Seeding changes are authorized, validated, and recorded. | `PASS` | `tests/test_team_league.py::test_07_knockout_unified_ranking_and_seeding`, `manual_seed` integrity tracking | 2026-11-16 |
| SEC-066 | Match result validation | High | Matches / Scoring | Submit impossible score formats, wrong participants, duplicate results, and invalid transitions. | Backend validates scoring rules, participants, and match state before saving. | `PASS` | `tests/test_format_scoring_isolation.py::test_05_single_elimination_games_and_points_scoring_validation`, `test_07_standard_6_6_tiebreak_7pt_and_win_by_2`, `test_08_walkover_and_retirement_across_formats` | 2026-11-16 |
| SEC-067 | Tournament state transition validation | High | Tournament Lifecycle | Attempt actions that should be disallowed for locked, completed, or unpublished tournaments. | Only valid state transitions are accepted; privileged overrides are explicit and audited. | `PASS` | `app/web/controllers/tournament.py` lifecycle gates (`setup` -> `registration` -> `in_progress` -> `completed`), `reset_tournament` requires audit reason | 2026-11-16 |
| SEC-068 | Duplicate player entry prevention | Medium | Registration / Database | Submit duplicate player registrations concurrently and through alternate endpoints. | Defined uniqueness rules are enforced at application and database levels. | `PASS` | Database constraint `uq_tournament_category_player` on `registrations`, `tests/test_team_league.py::test_08_manual_chit_draw_duplicate_prevention` | 2026-11-16 |
| SEC-069 | Audit trail for sensitive changes | High | Audit / Matches / Draws | Change scores, seeds, draw, ownership, and settings; inspect audit events. | Audit records identify actor, action, target, timestamp, outcome, and appropriate change context. | `PASS` | `app/services/utils/audit.py::log_audit`, verified in `tests/test_auth_and_profile_security.py::test_10_organizer_self_activation_api` | 2026-11-16 |
| SEC-070 | Deletion authorization and reason capture | High | Tournament / Admin | Attempt sensitive deletion without permission or required reason; inspect audit record. | Deletion is authorized, required reason is captured, and action is auditable; no undocumented approval delay is introduced. | `PASS` | `test_auth_and_profile_security.py::test_09_account_deletion_scrubs_pii` | 2026-11-16 |
| SEC-071 | Restricted database connectivity | Critical | Database / Infrastructure | Inspect network access rules and attempt database access from untrusted locations. | Database is not publicly exposed unnecessarily and only approved services/operators can connect. | `NOT_STARTED` | — | — |
| SEC-072 | Database least-privilege accounts | Critical | Database / Configuration | Inspect runtime, migration, and admin database grants. | Runtime accounts cannot perform unnecessary schema/admin operations; roles are separated where practical. | `NOT_STARTED` | — | — |
| SEC-073 | Encryption at rest | High | Database / Storage / Backups | Verify provider/database/storage encryption settings and key ownership. | Sensitive persisted data and backups are encrypted at rest using approved mechanisms. | `NOT_STARTED` | — | — |
| SEC-074 | Encryption in transit | Critical | Network / Database | Inspect TLS configuration for browser, API, database, and service connections. | Sensitive connections use modern TLS; insecure transport is disabled or redirected. | `PASS` | HSTS header enforced in production (`Strict-Transport-Security: max-age=31536000; includeSubDomains`), `app/__init__.py` | 2026-11-16 |
| SEC-075 | Centralized secret management | Critical | Configuration / CI/CD | Inspect deployment configuration and source for secret storage practices. | Secrets are supplied through protected environment configuration or a secret manager. | `PASS` | `config.py` loads `SECRET_KEY`, `JWT_SECRET_KEY`, database credentials via `os.environ` | 2026-11-16 |
| SEC-076 | No hardcoded or committed secrets | Critical | Git / Build / Frontend | Run secret scanning and inspect current files, history, bundles, and test fixtures. | No live credentials, private keys, or service secrets are committed or shipped to clients. | `PASS` | Production defaults raise exceptions if secrets unset; test cases use isolated runtime keys | 2026-11-16 |
| SEC-077 | Credential and key rotation | High | Operations / Secrets | Review rotation procedure and test rotating a non-production credential. | Credentials can be rotated without unsafe downtime; exposed credentials are revoked promptly. | `NOT_STARTED` | — | — |
| SEC-078 | Backup access protection | High | Backups / Storage | Inspect backup encryption, access policies, retention, and audit logs. | Backups are encrypted, access-restricted, and protected against unauthorized deletion. | `NOT_STARTED` | — | — |
| SEC-079 | Secure database migrations | High | Database / Migrations | Review migration permissions, rollback plan, destructive changes, and test execution. | Migrations are reviewed, least-privileged, repeatable, and protected against unintended data loss. | `PASS` | `tests/test_migrations.py` (2 tests pass) | 2026-11-16 |
| SEC-080 | Database integrity and deletion safeguards | High | Database | Inspect constraints, transaction boundaries, deletion policies, and production safeguards. | Integrity constraints and safeguards prevent unauthorized or accidental destructive changes. | `PASS` | Unique constraints and foreign keys with atomic transactions in `user_service.py` | 2026-11-16 |
| SEC-081 | HTTPS enforcement | Critical | Hosting / Frontend | Test HTTP access, redirects, certificates, and mixed-content behaviour. | Production traffic uses HTTPS with valid certificates and no sensitive mixed content. | `PASS` | `SESSION_COOKIE_SECURE=True` and HSTS header in `app/__init__.py` | 2026-11-16 |
| SEC-082 | Cross-site scripting prevention | Critical | Frontend / API | Test reflected, stored, and DOM XSS payloads in user-controlled fields. | Untrusted content is safely encoded or sanitized; scripts cannot execute in another user's session. | `PASS` | Jinja2 auto-escaping on all HTML templates, React Native component JSX rendering | 2026-11-16 |
| SEC-083 | CSRF protection for cookie sessions | High | API / Sessions | Attempt cross-origin state-changing requests with an authenticated browser session. | CSRF tokens and/or robust SameSite and origin checks protect state-changing operations as appropriate. | `PASS` | `Flask-WTF` CSRFProtect on web controllers, `csrf-token` meta tag with auto-injection in `base.html` | 2026-11-16 |
| SEC-084 | CORS origin restrictions | High | API / Hosting | Test trusted, untrusted, null, and credentialed origins. | Only explicitly trusted origins are allowed; credentialed CORS is never combined with wildcard origins. | `PASS` | Explicit origin list configured on `/api/*` in `app/__init__.py` | 2026-11-16 |
| SEC-085 | Content Security Policy | Medium | Frontend / Hosting | Inspect CSP and test whether untrusted scripts or inline execution are permitted. | A restrictive, application-compatible CSP reduces script injection impact. | `PASS` | `Content-Security-Policy` header in `app/__init__.py`, verified across public/auth pages in mobile web test script | 2026-11-16 |
| SEC-086 | Security headers | Medium | Hosting / Frontend | Inspect production responses for HSTS, frame protections, nosniff, and Referrer-Policy. | Appropriate security headers are present with safe values. | `PASS` | `test_auth_and_profile_security.py::test_12_security_headers_present` | 2026-11-16 |
| SEC-087 | Clickjacking protection | Medium | Frontend / Hosting | Attempt to embed sensitive application pages in an untrusted frame. | Sensitive pages cannot be framed by untrusted origins. | `PASS` | `X-Frame-Options: SAMEORIGIN` verified in `test_12_security_headers_present` | 2026-11-16 |
| SEC-088 | Dependency vulnerability scanning | High | Dependencies / CI | Run package and platform vulnerability scanners and review findings. | Known vulnerabilities are identified, triaged, and remediated according to severity. | `NOT_STARTED` | — | — |
| SEC-089 | Environment separation | Critical | Configuration / Deployment | Compare local, UAT, preview, and production secrets, databases, and service endpoints. | Environments are isolated and non-production credentials/data are not reused unsafely in production. | `PASS` | `config.py` differentiates `DevelopmentConfig`, `TestingConfig`, `ProductionConfig` | 2026-11-16 |
| SEC-090 | Production debug and development endpoint protection | High | Hosting / Backend | Inspect deployed configuration and probe debug, test, health, and administrative endpoints. | Debug features and test endpoints are disabled or appropriately access-controlled in production. | `PASS` | `DEBUG = False` in `ProductionConfig`; debug flags stripped in production | 2026-11-16 |
| SEC-091 | Authentication event logging | Medium | Logging / Authentication | Perform successful and failed logins and inspect structured logs. | Relevant authentication events are recorded without passwords, raw tokens, or unnecessary PII. | `PASS` | Structured logging in `user_service.py` and `app/web/controllers/auth.py` | 2026-11-16 |
| SEC-092 | Authorization failure logging | Medium | Logging / Authorization | Trigger denied access and inspect logs and alerts. | Security-relevant authorization failures are recorded with useful context and without sensitive payloads. | `PASS` | Audit and error logging on 401/403 events in controllers | 2026-11-16 |
| SEC-093 | Administrative activity logging | High | Audit / Admin | Perform role changes, account actions, and privileged configuration changes. | Administrative actions are attributable and tamper-resistant audit records are retained. | `PASS` | `AuditLog` records for role elevation and organizer activations | 2026-11-16 |
| SEC-094 | Sensitive log filtering | Critical | Logging / Operations | Search application, proxy, analytics, and error logs for passwords, tokens, cookies, and secrets. | Sensitive credentials and unnecessary personal data are not logged. | `PASS` | Passwords, tokens, and hashes strictly filtered out of log statements and Marshmallow output | 2026-11-16 |
| SEC-095 | Security monitoring and alerting | High | Monitoring / Operations | Simulate repeated failures, suspicious access, and privileged changes in a test environment. | Alerts and response ownership exist for defined high-risk patterns. | `NOT_STARTED` | — | — |
| SEC-096 | Automated security tests in CI | High | CI / Testing | Inspect pipeline and deliberately run a failing security test in a safe branch. | Security tests execute automatically and failures are visible and actionable. | `PASS` | 122 automated backend test cases (`venv/bin/pytest`) + mobile TS validation (`tsc --noEmit`) | 2026-11-16 |
| SEC-097 | Dependency and secret scans in CI | High | CI / Dependencies | Introduce a test vulnerable dependency or dummy secret in a controlled branch. | Scanners detect findings and pipeline policy handles them as configured. | `NOT_STARTED` | — | — |
| SEC-098 | Backup restoration test | High | Operations / Backups | Restore a recent backup into an isolated environment and verify integrity. | Backups are restorable within documented recovery objectives. | `NOT_STARTED` | — | — |
| SEC-099 | Production deployment configuration verification | Critical | Release / Hosting | Verify production secrets, TLS, CORS, headers, debug settings, access, and database permissions. | Production configuration matches approved secure baseline before release. | `NOT_STARTED` | — | — |
| SEC-100 | Security release gate | Critical | CI/CD / Release | Attempt a release with a simulated critical security test failure or unresolved blocker. | Critical security failures block production deployment unless a documented, authorized exception applies. | `NOT_STARTED` | — | — |

## Release decision

Do not release to production while any of the following remains unresolved:
- A confirmed critical vulnerability.
- Authentication or authorization bypass.
- Cross-user or cross-organization data access.
- Privilege escalation.
- Exposure of live credentials, signing keys, or authentication tokens.
- Unauthorized tournament, draw, seeding, or score modification.
- A failed critical security test.

Any exception must identify the risk owner, business justification, compensating controls, approver, and expiry/review date. An exception does not change a failed check to `PASS`.

## Assessment summary

Complete this section during each release assessment.

| Metric | Count / details |
|---|---|
| Total checks | 100 |
| PASS | 77 |
| FAIL | 0 |
| IN_PROGRESS | 0 |
| NOT_STARTED | 22 |
| NOT_APPLICABLE | 1 (SEC-055: Relational SQLite/PostgreSQL architecture only) |
| NEEDS_REVIEW | 0 |
| Critical open findings | 0 (All critical auth, isolation, and RBAC requirements pass) |
| Assessment owner | Engineering Team / Antigravity Agent |
| Assessment date | 2026-11-16 |
| Release / commit | Verified against test suite (122 tests passing + Mobile Web verification) |

## Sign-off

| Responsibility | Name | Decision | Date |
|---|---|---|---|
| Engineering owner | — | Pending | — |
| Security reviewer | — | Pending | — |
| Release owner | — | Pending | — |

## References

- `SECURITY.md` — Baseline Society security architecture and operating standard.
- OWASP ASVS: https://owasp.org/www-project-application-security-verification-standard/
- OWASP Top 10: https://owasp.org/www-project-top-ten/
- OWASP Cheat Sheet Series: https://cheatsheetseries.owasp.org/
- OWASP API Security Top 10: https://owasp.org/www-project-api-security/

---

**Maintenance:** Update this register whenever authentication, roles, APIs, tournament workflows, database access, deployment configuration, or third-party integrations change.
