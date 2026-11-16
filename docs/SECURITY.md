# SECURITY.md

**Project:** Baseline Society  
**Document type:** Security architecture and operating standard  
**Status:** Baseline policy template — implementation must be verified against the repository  
**Target standard:** OWASP Application Security Verification Standard (ASVS) 5.0.0, Level 2 where applicable  
**Last updated:** 2026-11-16

> **Important:** This document defines required security outcomes. It does not certify that the application currently meets them. Controls must be verified in source code, configuration, tests, and the deployed environment before being marked implemented.

## 1. Purpose and scope

This document establishes the minimum security expectations for Baseline Society, a multi-user sports tournament platform that may include player accounts, organizers, administrators, academies, tournaments, draws, match schedules, scores, and related records.

It applies to:
- Web frontend and browser-side code.
- Backend services, API routes, middleware, and background jobs.
- Authentication, authorization, and account lifecycle workflows.
- Database schemas, queries, migrations, backups, and storage.
- Third-party integrations and external services.
- Local, UAT, staging, preview, and production environments.
- CI/CD pipelines, source control, monitoring, and operational procedures.

The actual technology stack and deployment topology must be confirmed from the repository. Do not assume a framework, database, identity provider, or hosting provider based on this document.

## 2. Security objectives

Baseline Society must:
1. Authenticate each user as a unique, real account.
2. Bind every authenticated request to the correct user identity.
3. Enforce authorization on the server for every protected operation.
4. Prevent one user or organization from accessing another's private records without explicit authorization.
5. Protect tournament integrity, including registrations, draws, seeding, match results, and score changes.
6. Protect credentials, tokens, personal information, and operational secrets.
7. Detect, record, and investigate security-relevant events.
8. Fail safely when authentication, authorization, validation, or security dependencies fail.
9. Keep development, UAT, and production data and credentials appropriately separated.
10. Verify security controls through repeatable tests before release.

## 3. Security principles

- **Deny by default:** Access is denied unless explicitly granted.
- **Least privilege:** Users, services, and database accounts receive only necessary permissions.
- **Server-side enforcement:** Frontend visibility is not an authorization control.
- **Per-request authorization:** Validate the actor's permissions and resource relationship for each protected operation.
- **Secure defaults:** New accounts and new resources start with restrictive permissions.
- **Defense in depth:** Use multiple complementary controls rather than relying on a single check.
- **Fail closed:** If authorization or required security validation cannot be completed, do not perform the operation.
- **Data minimization:** Return, store, and log only the data required for the purpose.
- **Auditability:** Important actions must be attributable to an authenticated actor.
- **No security by obscurity:** Hidden routes, UI controls, IDs, and client-side flags are not access controls.

## 4. Threat model

### 4.1 Assets to protect

- Account credentials, password reset tokens, sessions, and authentication tokens.
- User profile data and contact information.
- Role assignments, permission grants, and account status.
- Academy, organizer, player, and tournament relationships.
- Tournament registrations, player lists, draws, seeds, schedules, and results.
- Match scores, score-edit history, and tournament status.
- Audit logs, database backups, environment variables, signing keys, and API credentials.
- Availability and integrity of the application.

### 4.2 Threat actors and likely threats

Consider:
- Unauthenticated internet users probing public endpoints.
- Authenticated users attempting to access other users' or organizations' records.
- Malicious or compromised organizer/player accounts.
- Users attempting privilege escalation or unauthorized score/draw changes.
- Automated credential-stuffing, brute-force, scraping, and denial-of-service traffic.
- Malicious input targeting injection, XSS, CSRF, or unsafe file handling.
- Compromised dependencies, developer credentials, CI/CD secrets, or third-party services.
- Accidental misuse by privileged users.

### 4.3 Trust boundaries

Document and test the boundaries between:
- Browser and backend.
- Public and authenticated API routes.
- Authenticated identity and application roles.
- User/organization ownership and shared tournament access.
- Application services and database/storage services.
- CI/CD and deployment environments.
- Baseline Society and third-party integrations.

### 4.4 Minimum abuse cases

Tests must include, at minimum:
- User A changes a URL or request ID to read or modify User B's profile.
- A player changes a request to modify another player's score.
- An organizer accesses a tournament they do not manage.
- A regular user submits an admin role or account-status field during registration/profile update.
- A revoked user continues using an old session or token.
- An unauthenticated client calls a private API directly.
- A user replays a score update or deletion request.
- Malicious input is stored and later rendered to another user.
- A reset token is reused, expired, or used for a different account.
- A development credential or secret is accidentally included in a build or Git history.

## 5. Identity, registration, and authentication

### 5.1 Account identity

- Each account must have an immutable internal identifier.
- Email addresses or other login identifiers must be normalized consistently.
- Enforce uniqueness at the database level as well as in application logic.
- Registration must create the account associated with the submitted and verified identity.
- After login, the profile and all user-specific queries must derive identity from the validated server-side session/token—not from a client-supplied `userId`.
- Production must not silently authenticate as a demo, dummy, seed, or default user.
- Demo accounts, if required, must be explicitly isolated, clearly labelled, and disabled or inaccessible in production.

### 5.2 Passwords

- Prefer a managed identity provider where appropriate; otherwise use a modern password hashing function such as Argon2id. bcrypt may be used where supported and configured with an appropriate work factor.
- Never store plaintext passwords or reversibly encrypted passwords.
- Do not log passwords, password reset tokens, or authentication secrets.
- Enforce a sensible minimum length and screen against commonly compromised passwords. Avoid arbitrary composition rules that encourage predictable passwords.
- Permit password managers and paste.
- Reauthenticate users before high-risk account changes.
- Use generic authentication and recovery responses to reduce account enumeration.

### 5.3 Email verification and recovery

- Require proof of control of an email address before treating it as verified.
- Use cryptographically random, single-use, time-limited verification and reset tokens.
- Store only a secure representation/hash of one-time tokens where practical.
- Invalidate a token after successful use and invalidate relevant sessions after password reset.
- Rate-limit registration, verification resend, login, and recovery endpoints.
- Do not disclose whether an email address is registered through recovery responses.

### 5.4 Multi-factor authentication

- Provide MFA for privileged accounts and strongly encourage it for organizers.
- Support secure recovery procedures that do not bypass identity verification.
- Reauthentication should be required for sensitive actions such as changing MFA, changing credentials, or granting privileges.

## 6. Authorization and permissions

### 6.1 Authorization model

Implement a documented role/permission model appropriate to the actual product. Potential roles may include platform administrator, organizer, academy manager, coach, player, and read-only/support roles, but the repository's real roles must be authoritative.

For every protected operation, verify:
1. The request has a valid authenticated identity.
2. The account is active and eligible to act.
3. The actor has the required permission.
4. The actor is authorized for the specific target resource.
5. The requested state transition is valid.
6. The request cannot modify protected fields outside the operation's purpose.

### 6.2 Resource ownership and tenant isolation

- Treat object-level authorization as mandatory.
- Scope queries by the authenticated user's authorized organization/tournament/resource relationship.
- Do not rely on unguessable IDs as a substitute for authorization.
- Ensure list, search, export, detail, update, and delete endpoints apply equivalent access rules.
- Prevent cross-organization data leakage.
- Shared access must be explicit, revocable, and auditable.

### 6.3 Privileged operations

- Only an authorized platform administrator may grant or revoke platform-level privileges.
- Users must not assign their own role, permissions, account status, ownership, or verification state.
- Privilege changes must be audited and should require reauthentication for sensitive changes.
- Separate platform administration from tournament-level organizer permissions.
- Use MFA for privileged accounts where supported.

## 7. Tournament and sports data integrity

The backend must enforce tournament rules; the browser must not be trusted to enforce them.

- Validate tournament ownership or delegated management permission before changing tournament data.
- Validate player eligibility and prevent duplicate registrations according to the tournament's rules.
- Validate draw generation, seeding, and draw edits against the tournament state and authorized workflow.
- Validate score format, match participants, permitted score transitions, and match status.
- Restrict score entry and score correction to authorized roles.
- For sensitive score edits and deletions, record the actor, timestamp, target, before/after values where appropriate, and the required reason.
- Prevent changes to locked or completed tournaments unless an explicitly authorized override workflow exists.
- Use database transactions and concurrency controls for operations where partial updates could corrupt tournament state.
- Make operations idempotent where retries could otherwise create duplicate registrations or actions.
- Do not treat a client-provided organizer ID, player ID, tournament ID, or role as proof of authorization.

## 8. API and application security

- Protect all private endpoints with authentication and authorization middleware or equivalent server-side controls.
- Maintain an inventory of routes and identify public, authenticated, and privileged endpoints.
- Validate request bodies, query parameters, path parameters, headers, and uploaded files against explicit schemas.
- Use parameterized database queries or safe ORM APIs.
- Avoid unsafe dynamic SQL, shell execution, template evaluation, and deserialization of untrusted input.
- Allowlist writable fields; avoid mass assignment.
- Apply request body, upload, pagination, and execution limits.
- Apply rate limits to authentication, search, exports, invitations, and expensive operations.
- Return generic client errors; do not expose stack traces, SQL, internal paths, secrets, or infrastructure details.
- Configure CORS for known trusted origins; do not use wildcard origins with credentialed requests.
- If cookie-based authentication is used, apply CSRF protections to state-changing requests.
- If bearer tokens are used, validate signature, issuer, audience, expiry, and permitted algorithms; support revocation/rotation where needed.
- Use TLS for all external traffic and service-to-service connections.

## 9. Frontend and browser security

- Treat all browser input and browser state as untrusted.
- Render user-controlled content as text by default; sanitize only when rich HTML is an intentional feature.
- Avoid unsafe DOM APIs and unsafe HTML rendering.
- Configure a Content Security Policy appropriate to the deployed frontend.
- Configure security headers, including HSTS on HTTPS deployments, frame protections, `X-Content-Type-Options`, and an appropriate `Referrer-Policy`.
- Use secure cookie attributes when cookies are used.
- Do not embed private API keys or service credentials in frontend bundles.
- Do not rely on hidden buttons, route guards, disabled controls, or local storage flags for authorization.
- Avoid storing long-lived sensitive tokens in browser-accessible storage.
- Ensure production source maps and debug endpoints do not expose sensitive implementation details.

## 10. Database, storage, encryption, and secrets

- Use separate, least-privileged database credentials for application runtime, migrations, and administration.
- Do not expose database credentials or direct database connectivity to the browser.
- Enforce foreign keys, uniqueness, and other integrity constraints in the database where appropriate.
- Encrypt sensitive data at rest using the capabilities of the hosting/database provider.
- Encrypt backups and restrict backup access.
- Use TLS for database and storage connections where supported.
- Keep secrets in an approved secret manager or protected deployment environment variables.
- Never commit secrets to source control or include them in client bundles, logs, test fixtures, or documentation.
- Rotate credentials after suspected exposure and periodically according to operational risk.
- Restrict object-storage access and use short-lived signed URLs where private file access is required.
- Define data retention and deletion policies, including backups and logs.

## 11. Logging, monitoring, and audit trails

Record security-relevant events such as:
- Successful and failed authentication.
- Password reset and account recovery events.
- MFA enrollment and changes.
- Authorization failures and suspicious access attempts.
- Role and permission changes.
- Account suspension/deactivation.
- Tournament ownership changes.
- Score edits, draw edits, seeding changes, and sensitive deletions.
- Administrative exports and other high-risk actions.

Each applicable audit event should include:
- Actor ID (or an explicit unauthenticated/system actor).
- Action and target resource.
- Timestamp in a consistent timezone (prefer UTC).
- Outcome.
- Correlation/request ID.
- Reason and before/after state where appropriate and safe.

Do not log passwords, raw tokens, session cookies, secret keys, or unnecessary sensitive personal data. Protect logs against tampering and unauthorized access. Define alerting and retention appropriate to risk and legal obligations.

## 12. Infrastructure, dependencies, and deployment

- Keep local, UAT/staging, preview, and production environments isolated.
- Use separate credentials, databases, storage buckets, and third-party keys per environment.
- Restrict production access to authorized personnel and services.
- Keep runtimes, frameworks, operating-system packages, and dependencies supported and patched.
- Scan dependencies and container/build artifacts where applicable.
- Pin or lock dependencies and review unexpected dependency changes.
- Protect CI/CD secrets and restrict deployment permissions.
- Require review for security-sensitive changes.
- Disable debug mode, development routes, test credentials, and verbose errors in production.
- Configure backups and periodically test restoration.
- Ensure security headers, TLS, allowed origins, and production secrets are verified in the deployed environment.

## 13. Security testing and release gate

Use a combination of:
- Static analysis and secret scanning.
- Dependency and vulnerability scanning.
- Unit and integration tests for authorization and validation.
- API security tests.
- Dynamic testing against a non-production environment.
- Manual review of high-risk workflows.
- Backup restoration tests.
- Configuration checks on the deployed environment.

A release must not proceed when:
- A confirmed critical vulnerability remains unresolved.
- Authentication or authorization can be bypassed.
- Cross-user or cross-organization access is possible.
- Privilege escalation is possible.
- Sensitive credentials are exposed.
- A required security control is failing or has not been assessed and is a release blocker under the team's risk policy.

Document accepted risks with an owner, rationale, compensating controls, approval, and expiry/review date. Do not silently convert a failed check into a pass.

## 14. Incident response

Maintain a response procedure that covers:
1. Report and triage.
2. Severity assessment and incident owner assignment.
3. Containment (for example, revoke sessions, rotate credentials, disable affected functionality).
4. Evidence preservation and secure log review.
5. Eradication and remediation.
6. Recovery and validation.
7. Required user, provider, or regulatory notifications.
8. Post-incident review and preventive actions.

For suspected credential or token exposure, revoke or rotate affected credentials promptly. Preserve evidence without retaining unnecessary personal data.

## 15. Vulnerability reporting

Provide a monitored security contact or private reporting channel before public production launch. Do not publish sensitive vulnerability details or credentials in public issue trackers. Acknowledge reports, assess severity, coordinate remediation, and communicate resolution responsibly.

## 16. Ownership and review

- Engineering owns implementation and remediation.
- The release owner ensures required checks are reviewed before deployment.
- Platform administrators protect privileged accounts and operational access.
- Security exceptions require documented approval and a review date.

Review this document:
- Before major authentication, authorization, database, or infrastructure changes.
- Before production launch.
- After a material security incident.
- At least annually, or more frequently where risk requires.

## 17. Standards and references

Use these as implementation references; confirm the applicable version when performing an assessment:
- OWASP Application Security Verification Standard (ASVS): https://owasp.org/www-project-application-security-verification-standard/
- OWASP Top 10: https://owasp.org/www-project-top-ten/
- OWASP Cheat Sheet Series: https://cheatsheetseries.owasp.org/
- OWASP API Security Top 10: https://owasp.org/www-project-api-security/
- NIST Digital Identity Guidelines (SP 800-63): https://pages.nist.gov/800-63-3/
- CWE: https://cwe.mitre.org/

---

## Appendix A — Implementation truthfulness

This document is a security target and operating policy. It must not be represented as proof of compliance or certification. A control is implemented only when supported by repository evidence, automated/manual test evidence, and—where relevant—verification in the deployed environment.
