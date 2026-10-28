# TourneyPro — External Integrations & Cloud Infrastructure (INTEGRATIONS.md)

**Document Status:** Approved  
**Source of Truth:** Inherits from [`MCP.md`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/MCP.md), [`ARCHITECTURE.md`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/ARCHITECTURE.md), and [`FEATURES.md`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/FEATURES.md)  
**Infrastructure Target:** Cloud Native (Vercel Serverless + Supabase Managed PostgreSQL)  
**Last Updated:** October 2026  

---

## 1. Cloud Architecture Overview

TourneyPro is architected as a hybrid serverless/cloud-native platform utilizing managed microservices:

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

TourneyPro configures `psycopg` (v3) in [`config.py`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/config.py) specifically for PgBouncer:

```python
if db_url and db_url.startswith('postgresql'):
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'connect_args': {
            'prepare_threshold': None  # Disables client-side prepared statements
        }
    }
```

### 2.2 Connection String Sanitization
To prevent crashes caused by trailing spaces or quote marks in environment variables:
```python
db_url = os.environ.get('DATABASE_URL')
if db_url:
    db_url = db_url.strip().strip("'\"")
    if db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql+psycopg://', 1)
```

### 2.3 Automated Schema Reconciliation (`scripts/sync_db_schema.py`)
Because serverless environments should avoid running slow DDL migrations on cold boot, production schema synchronization runs via GitHub Actions during deployment:
1. Connects to the Supabase database.
2. Compares declared SQLAlchemy model columns against the active PostgreSQL catalog (`information_schema.columns`).
3. Executes non-destructive `CREATE TABLE` and `ALTER TABLE ... ADD COLUMN` statements for any newly introduced fields.

---

## 3. Vercel Serverless Hosting Integration

### 3.1 Routing & Build Configuration ([`vercel.json`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/vercel.json))
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
In [`app/__init__.py`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/app/__init__.py), table inspection queries are bypassed when executing inside Vercel's serverless runtime:
```python
if not os.environ.get('VERCEL'):
    db.create_all()
    # Execute column verification...
```
This guarantees that serverless lambdas start in < 400ms without exhausting connection pools on cold start.

---

## 4. Vector PDF Rendering Engine

High-performance document rendering is powered by `xhtml2pdf` (v0.2.17) and `reportlab` (v4.5.1):

### 4.1 Architecture
* `DrawExportAdapter`: Flattens the hierarchical match database records into a clean geometric matrix with calculated connector pins.
* `OrderOfPlayExportAdapter`: Formats court columns and hourly match slots into a printable landscape table.
* `ParticipantsExportAdapter`: Generates official player rosters, seeding ranks, and check-in rosters.

### 4.2 HTTP 304 ETag Caching
To minimize CPU utilization during heavy tournament finals:
```python
def make_pdf_response(pdf_bytes: bytes, filename: str, etag: Optional[str] = None):
    if not etag:
        etag = hashlib.md5(pdf_bytes).hexdigest()

    if_none_match = request.headers.get("If-None-Match")
    if if_none_match and if_none_match.strip('"') == etag.strip('"'):
        return Response(status=304)  # 0-byte instantaneous response

    response = make_response(pdf_bytes)
    response.headers["Content-Type"] = "application/pdf"
    response.headers["ETag"] = f'"{etag}"'
    response.headers["Cache-Control"] = "private, max-age=120, must-revalidate"
    return response
```

---

## 5. Spreadsheet Roster Import / Export

* Powered by `openpyxl` (v3.1.5).
* Organizers can export registered participants into an `.xlsx` workbook, modify seed numbers or check-in statuses, and re-import the file with automated validation.

---

## 6. Payment Gateway Integrations

### 6.1 Current: Manual UPI Verification Workflow
* Organizers configure their personal UPI ID (`payment_upi_id`) in tournament setup.
* Players make direct payment via any UPI application (Google Pay, PhonePe, Paytm).
* Players submit their 12-digit UPI Transaction Reference Number during registration.
* Organizers verify payments in the Admin Registration Hub with 1-click Approval.

### 6.2 Planned: Stripe Checkout & Webhook Integration
* Automated redirection to hosted Stripe Checkout sessions.
* Webhook endpoint: `POST /api/v1/integrations/stripe/webhook` verifying signature `stripe-signature`.
* Automatically updates `Registration.payment_status = 'paid'` and `Registration.status = 'approved'`.

---

## 7. Automated Notification Integrations (Planned)

### 7.1 Twilio SMS Dispatch
* Used for real-time player dispatch:
  ```python
  client.messages.create(
      body="TourneyPro Alert: You are Up Next on Court 2 for Men's Singles. Please report in 10 minutes.",
      from_=os.environ.get('TWILIO_PHONE_NUMBER'),
      to=player.mobile
  )
  ```

### 7.2 SendGrid Email Engine
* Sends branded HTML tournament confirmations, schedule change notices, and attached PDF draw sheets upon bracket generation.
