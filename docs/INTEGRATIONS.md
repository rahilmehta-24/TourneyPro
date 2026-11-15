# The Baseline Society — External Integrations & Cloud Infrastructure (INTEGRATIONS.md)

**Document Status:** Approved  
**Source of Truth:** Inherits from [`MCP.md`](MCP.md), [`ARCHITECTURE.md`](ARCHITECTURE.md), and [`FEATURES.md`](FEATURES.md)  
**Infrastructure Target:** Cloud Native (Vercel Serverless + Supabase Managed PostgreSQL)  
**Last Updated:** November 2026  

---

## 1. Cloud Architecture Overview

The Baseline Society is architected as a hybrid serverless/cloud-native platform utilizing managed microservices:

```
┌────────────────────────────────┐
│      Edge Routing & CDN        │
│          (Vercel)              │
└───────────────┬────────────────┘
                │ WSGI Invocations
                ▼
┌────────────────────────────────┐
│     Serverless Python API      │
│      (@vercel/python)          │
└───────────────┬────────────────┘
                │
    ┌───────────┼───────────┬───────────────┐
    │           │           │               │
    ▼           ▼           ▼               ▼
┌────────┐ ┌─────────┐ ┌─────────┐ ┌────────────────┐
│Supabase│ │xhtml2pdf│ │openpyxl │ │Payment / Alerts│
│Postgres│ │VectorPDF│ │Excel R/W│ │(Stripe/Twilio) │
└────────┘ └─────────┘ └─────────┘ └────────────────┘
```

---

## 2. Supabase (Managed PostgreSQL) Integration

### 2.1 Connection Pooling & PgBouncer Compatibility
Supabase utilizes PgBouncer in **Transaction Pooling Mode** to multiplex hundreds of client connections. Standard PostgreSQL drivers that rely on prepared statement caching will trigger `prepared statement already exists` fatal errors under transaction poolers.

The Baseline Society configures `psycopg` (v3) in [`config.py`](config.py) specifically for PgBouncer:

```python
if db_url and db_url.startswith('postgresql'):
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'connect_args': {
            'prepare_threshold': None  # Disables client-side prepared statements
        }
    }
```

### 2.2 Connection String Sanitization & Pooler Selection
Use the Supabase **transaction pooler** connection string (port 6543) for the serverless app; use the direct or session connection only for migrations and long-running admin scripts. Copy the exact string from the Supabase dashboard (Connect panel).

To prevent crashes caused by trailing spaces, quote marks, or the wrong driver prefix:
```python
db_url = os.environ.get('DATABASE_URL')
if db_url:
    db_url = db_url.strip().strip("'\"")
    for prefix in ('postgres://', 'postgresql://'):          # both must select psycopg 3
        if db_url.startswith(prefix):
            db_url = 'postgresql+psycopg://' + db_url[len(prefix):]
            break
```
Without the second prefix, a standard `postgresql://` URL makes SQLAlchemy import psycopg2, which this project does not install. Also require `sslmode=require` for remote databases.

### 2.3 Automated Schema Reconciliation (`scripts/sync_db_schema.py`)
Because serverless environments should avoid running slow DDL migrations on cold boot, production schema synchronization runs via GitHub Actions during deployment:
1. Connects to the Supabase database.
2. Compares declared SQLAlchemy model columns against the active PostgreSQL catalog (`information_schema.columns`).
3. Executes non-destructive `CREATE TABLE` and `ALTER TABLE ... ADD COLUMN` statements for any newly introduced fields.

---

## 3. Vercel Serverless Hosting Integration

### 3.1 Routing & Build Configuration ([`vercel.json`](vercel.json))
```json
{
  "builds": [
    {
      "src": "run.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "run.py"
    }
  ]
}
```

### 3.2 Cold-Start Optimization
In [`app/__init__.py`](app/__init__.py), table inspection queries are bypassed when executing inside Vercel's serverless runtime:
```python
if not os.environ.get('VERCEL'):
    db.create_all()
    # Execute column verification...
```
This keeps cold starts fast and avoids exhausting connection pools; measure cold-start latency in your own region rather than relying on a fixed target.

### 3.3 Real-Time Limitation
Vercel serverless functions cannot keep WebSocket connections open, so `Flask-SocketIO` is not deployable on this platform. Use CDN-cached polling, a managed realtime service (Supabase Realtime, Ably, Pusher), or a container host; see [`ARCHITECTURE.md`](ARCHITECTURE.md) §7.

### 3.4 Secrets & Environment
Secrets (`SECRET_KEY`, `JWT_SECRET_KEY`, `DATABASE_URL`, payment and messaging keys) live only in the Vercel/GitHub secret stores. Use separate values per environment (production, UAT, local), restrict who can read them, and rotate on any suspected exposure.

---

## 4. Vector PDF Rendering Engine

High-performance document rendering is powered by `xhtml2pdf` (v0.2.17) and `reportlab` (v4.5.1):

### 4.1 Architecture
* `DrawExportAdapter`: Flattens the hierarchical match database records into a clean geometric matrix with calculated connector pins.
* `OrderOfPlayExportAdapter`: Formats court columns and hourly match slots into a printable landscape table.
* `ParticipantsExportAdapter`: Generates official player rosters, seeding ranks, and check-in rosters.

### 4.2 HTTP 304 ETag Caching
To minimize CPU utilization during heavy tournament finals the ETag must be known **before** rendering. Hashing the finished PDF cannot save CPU, because the document has already been generated.
```python
def make_pdf_response(render_pdf, filename, version_stamp):
    # Authorization and draw_published checks happen BEFORE this call.
    etag = hashlib.sha256(version_stamp.encode()).hexdigest()[:32]
    client_tags = {x.strip().removeprefix("W/").strip('"')
                   for x in request.headers.get("If-None-Match", "").split(",")}
    if etag in client_tags:
        return Response(status=304, headers={"ETag": f'"{etag}"'})   # 0-byte response, no rendering

    response = make_response(render_pdf())                           # render only on a miss
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = f'inline; filename="{filename}"'
    response.headers["ETag"] = f'"{etag}"'
    response.headers["Cache-Control"] = "private, max-age=120, must-revalidate"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response
```
`version_stamp` combines the category's latest `lock_version` / `completed_at`, the `draw_published` flag, and the template version. Never return `304` before the caller is authorized, and keep `Cache-Control: private` so shared caches cannot store draft or roster PDFs.

### 4.3 Headless Chrome Document Pipeline
For multi-page illustrated documents such as [`TourneyPro_User_Manual.pdf`](TourneyPro_User_Manual.pdf), The Baseline Society uses a high-fidelity Chrome Headless compilation pipeline (`scripts/generate_user_manual.py`):
```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --headless=new \
  --disable-gpu \
  --no-pdf-header-footer \
  --print-to-pdf="docs/TourneyPro_User_Manual.pdf" \
  "docs/USER_MANUAL.html"
```
The path shown is for macOS; on Linux or CI use `google-chrome` or `chromium`. This renders modern CSS3 flexbox, glassmorphic badges, page-break rules (`page-break-after: always`), and base64 embedded UI screenshots with print perfection.

### 4.4 Safe Rendering Rules
* **Escape all user-supplied text** (names, notes, venue) before it enters an HTML template that `xhtml2pdf` renders.
* **No remote fetching:** configure `link_callback` to resolve only local allow-listed assets (logo, fonts); reject any `http://` or `https://` URL so a crafted name cannot trigger server-side requests (SSRF).
* **Fonts:** `xhtml2pdf` cannot load web fonts. Register local TTF files with ReportLab (for example Inter and Cormorant Garamond) so exports match [`DESIGN.md`](DESIGN.md).
* **Limits:** cap participants per document and set a render timeout to prevent resource exhaustion.

---

## 5. Spreadsheet Roster Import / Export

* Powered by `openpyxl` (v3.1.5).
* Organizers can export registered participants into an `.xlsx` workbook, modify seed numbers or check-in statuses, and re-import the file with automated validation.
* **Export safety (formula injection):** any text cell beginning with `=`, `+`, `-`, or `@` is prefixed with an apostrophe or stored as an explicit string, so a malicious player name cannot execute formulas when staff open the file.
* **Import safety:** accept only `.xlsx`, maximum 2 MB and 2,000 rows, open in read-only mode with `data_only=True`, reject macros and external links, validate every column type and length, and run the import inside a transaction that rolls back entirely on any error. Only owners and managers may import, and each import is audit-logged.

---

## 6. Payment Gateway Integrations

### 6.1 Current: Manual UPI Verification Workflow
* Organizers configure their personal UPI ID (`payment_upi_id`) in tournament setup.
* Players make direct payment via any UPI application (Google Pay, PhonePe, Paytm).
* Players submit their 12-digit UPI Transaction Reference Number during registration. The value is format-validated and must be unique within the tournament, so one payment cannot approve several entries.
* Organizers verify payments in the Admin Registration Hub with 1-click Approval.

### 6.2 Planned: Stripe Checkout & Razorpay Webhook Integration
* Automated redirection to hosted Checkout sessions created **server-side**; the amount and currency come from `Registration.amount_due`, never from the browser.
* Webhook endpoint: `POST /api/v1/integrations/stripe/webhook` (and a Razorpay equivalent) is the only CSRF-exempt route outside the API blueprint.
* **Verification:** read the raw request body, verify the `Stripe-Signature` header with `stripe.Webhook.construct_event` and the webhook secret (a 5-minute timestamp tolerance blocks replays); for Razorpay verify `X-Razorpay-Signature` (HMAC-SHA256) in constant time.
* **Idempotency:** store processed event IDs in a table with a unique constraint and ignore duplicates.
* **Reconciliation:** confirm that the paid amount, currency, and registration ID match before setting `Registration.payment_status = 'paid'` and `Registration.status = 'approved'`.
* **Keys:** use restricted API keys with only the permissions needed; keep test and live keys in separate environments.
* **Refunds** triggered by category cancellation are audit-logged.

---

## 7. Automated Notification Integrations (Planned)

### 7.1 Twilio SMS Dispatch
* Used for real-time player dispatch:
  ```python
  client.messages.create(
      body="The Baseline Society Alert: You are Up Next on Court 2 for Men's Singles. Please report in 10 minutes.",
      from_=os.environ.get('TWILIO_PHONE_NUMBER'),
      to=player.mobile
  )
  ```
* Send only to numbers whose owner consented to alerts and provide an opt-out. For SMS in India, sender IDs and message templates typically must be registered on the telecom DLT platform before launch; confirm current requirements with the provider.
* Rate-limit sends per tournament, never include other players' contact data in messages, and keep credentials in the secret store.

### 7.2 SendGrid Email Engine
* Sends branded HTML tournament confirmations, schedule change notices, and attached PDF draw sheets upon bracket generation.
* Create the API key with **restricted access (Mail Send only)**, not Full Access. Verify the sending domain (SPF/DKIM) and attach only published draw sheets.

## 8. Third-Party Credential Handling
| Credential | Stored in | Rule |
| :--- | :--- | :--- |
| Stripe / Razorpay keys, webhook secrets | Platform secret store | Restricted keys; separate test and live; rotate on exposure |
| Twilio SID and token | Platform secret store | Message-only permissions where possible |
| SendGrid key | Platform secret store | Mail Send scope only |
| Supabase service-role key | Server only | Never shipped to browsers or committed |

Never paste real credentials into chat tools, tickets, or AI prompts; use sandbox or test keys when working with agents.
