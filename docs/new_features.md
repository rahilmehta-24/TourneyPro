# TourneyPro V2: Expansion & Ecosystem Implementation Plan

This document outlines the architectural and implementation strategy for the next major evolution of TourneyPro, focusing on Player Ecosystems, Dynamic Scheduling, and Real-Time Operations.

Because this is a massive undertaking that touches the core database schema, real-time infrastructure, and third-party APIs, it is structured into **Three Phases**. 

> [!IMPORTANT]
> **Status: Phase 1 Partially Completed**
> The foundational "Smart Registration" (Guest Flow without accounts) and "Unified Organizer Wizard" have been built and verified. Future phases like WebSockets and dynamic automated court assignment remain in the pipeline.

---

## Phase 1: Player & Team Ecosystem
This phase transforms the app from an organizer-only tool into a community platform.

### 1. Player Profiles & Portfolios
- **Database**: Add `avatar_url` and `bio` to the `Player` model.
- **Backend**: Create a public `/player/<id>` route displaying a comprehensive portfolio (Win Rates, Total Points, Historical Matches).
- **Frontend**: Add a Dashboard UI for users to manage their player profiles and upload avatars.

### 2. Team & Club Management
- **Database**: 
  - Create a new `Team` model (`id`, `name`, `owner_id`, `logo_url`).
  - Create a `TeamMember` mapping table.
  - Add `team_id` to the `Participant` model.
- **Backend**: Add Team creation forms, invite systems, and leaderboard aggregation by Team.

### 3. Self-Registration & Ticketing (✅ Partially Implemented)
- **Database**: `payment_status` logic integrated.
- **Workflow (Smart Registration Built):**
  1. Organizer opens registration and sets an entry fee.
  2. Public "Register" button enables both logged-in and Guest (unauthenticated) checkout flow.
  3. Guest players are linked to a standalone Player profile without forcing standard authentication (`anonymous_registrations` mapping).
  4. *(Pending)* Full Stripe webhook automation.

---

## Phase 2: Enhanced Tournament Operations
This phase modernizes the bracket view with real-time capabilities and automated logistics.

### 1. Live Score Updates (WebSockets)
- **Infrastructure**: Install and configure `Flask-SocketIO` to replace the standard Flask development server.
- **Backend Event Emission**: When a referee/admin updates a match score via the existing modal, emit a `match_score_updated` socket event containing the match ID and new score.
- **Frontend Receiver**: Brackets and public viewing pages subscribe to the tournament's specific WebSocket room. When a score event is received, JavaScript dynamically updates the DOM without requiring a page refresh.

### 2. Dynamic Match Scheduling & Court Assignment
- **Database**: Add `court_id` or `court_name` to the `Match` model. Add `operating_hours` and `num_courts` to `Tournament`.
- **Algorithm Engine**: Build an automated scheduler that:
  - Calculates round dependencies (e.g., Round 2 cannot start until Round 1 is finished).
  - Assigns courts using a round-robin or first-available method.
  - Predicts match durations to generate accurate time slots.
- **Frontend**: Build an "Up Next / Court Schedule" public view for players to track.

### 3. Native-Grade Mobile Web App Experience (✅ Implemented)
- **Safe-Area Shell & Off-Canvas Navigation:** Integrated `viewport-fit=cover` and dynamic viewport units (`dvh`) with a glassmorphic slide-out drawer (`#navbarCollapseWrapper`) and persistent bottom thumb bar (`#mobileBottomBar`).
- **Knockout Bracket Touch Panning:** Hardware-accelerated `touchstart`, `touchmove`, and `touchend` events with round-by-round pill navigation tabs (`scrollToBracketRound`), fully preserving horizontal SVG Bézier connector geometry.
- **Bottom-Sheet Match Scoring:** Transforms modal dialogs on `≤ 640px` into ergonomic bottom sheets with sticky action buttons and `inputmode="numeric" pattern="[0-9]*"`.
- **1-Tap Mobile UPI Intent:** Direct `upi://pay?pa=...` deep linking into installed payment apps (GPay, PhonePe, Paytm) and 1-tap clipboard copy button, resolving the mobile on-screen QR scanning impossibility.

### 4. Enterprise RBAC & Staff Delegation (✅ Implemented)
- **Database Schema**: Introduced `tournament_staff` relational mapping table (`tournament_id`, `user_id`, `role`, `created_at`).
- **Granular Roles**:
  - `owner` / `tournament_admin`: Complete tournament authority.
  - `desk`: Operational logistics, check-ins, seed allocations, and court assignment.
  - `umpire`: Court-side score reporting and rubber completion.
- **Staff Appointment Portal**: `/tournaments/<slug>/staff` allows organizers to appoint registered users, modify permissions, or revoke staff access with 1 click.

### 5. Quick Court PIN Scorekeeping Mode (✅ Implemented)
- **Database**: Added `court_pin` (4-digit numeric code) to `Tournament` model.
- **Workflow**:
  1. Organizer defines a court PIN in tournament settings.
  2. Court scorers navigate to `/tournaments/<slug>/court-pin` on on-court tablets.
  3. Scorers authenticate using the PIN without needing personal user accounts.
  4. Scorer session grants direct score reporting permissions for all matches on that court.

### 6. Draw Publication State Machine (✅ Implemented)
- **Database**: Added `draw_published` boolean column to `Category` model.
- **Privacy Controls**:
  - Generated brackets default to Draft mode (`draw_published = False`).
  - Spectators and players visiting draft draws receive a friendly banner notice: *"Draws for this event are being finalized by the tournament committee"*.
  - Organizers preview, adjust seeds, and inspect bracket balance in draft mode before publishing via 1-click `/categories/<id>/toggle-publish`.
  - Draw PDF export is locked until published.

### 7. Match Integrity & Optimistic Concurrency Control (✅ Implemented)
- **Anti-Conflict of Interest Guard**: Active participants (or competing team captains in team leagues) are strictly blocked from officiating or scoring their own matches (`HTTP 403 Forbidden`).
- **Optimistic Concurrency Control (`lock_version`)**: Matches track a monotonic version counter. Score updates submit `lock_version`; mismatched versions reject with `HTTP 409 Conflict`, preventing concurrent umpire score overwrites.

### 8. End-User Manual Suite & Vector PDF Guide (✅ Implemented)
- Created clean, non-technical web operational manual [`docs/USER_MANUAL.md`](USER_MANUAL.md) for non-technical organizers, umpires, captains, and players.
- Built interactive HTML version with base64 embedded screenshots [`docs/USER_MANUAL.html`](USER_MANUAL.html).
- Compiled publication-ready 6-page PDF manual [`docs/TourneyPro_User_Manual.pdf`](TourneyPro_User_Manual.pdf) via Chrome headless engine.

---

## Phase 3: Communication & Engagement
This phase focuses on automated participant outreach.

### 1. Notification Engine
- **Database**: Add `phone_number` and `notification_preferences` to the `User`/`Player` models.
- **Integrations**: 
  - **Twilio**: For SMS notifications.
  - **SendGrid**: For Email notifications.
- **Triggers**:
  - *Bracket Generated*: "Your draw is ready! You are playing [Opponent Name]."
  - *Court Assignment*: "You are Up Next on Court 3 in 15 minutes."
  - *Schedule Delays*: Mass alerts to all active participants.

> [!WARNING]
> **API Keys Required**
> Phase 1 (Ticketing) requires a Stripe Account. Phase 3 requires Twilio and SendGrid accounts. You will need to provide these API credentials (or let me use sandbox/test modes) when we reach those stages. See the guide below for instructions on generating these keys.

### 🔑 API Key Generation Guide

**1. Stripe API Keys (For Phase 1 - Ticketing)**
*   Go to [dashboard.stripe.com](https://dashboard.stripe.com/register) and create a free account.
*   Once logged in, look for the "Developers" toggle in the top right and ensure **"Test Mode"** is ON.
*   Click on the **"API keys"** tab.
*   You will need to copy the **"Publishable key"** (starts with `pk_test_...`) and the **"Secret key"** (starts with `sk_test_...`).

**2. Twilio API Keys (For Phase 3 - SMS)**
*   Go to [twilio.com](https://www.twilio.com/try-twilio) and sign up for a free trial.
*   After verifying your email and phone number, go to your Twilio Console Dashboard.
*   Scroll down to the **"Account Info"** section.
*   You will need to copy the **"Account SID"** and the **"Auth Token"**.
*   You will also need to click "Get a trial phone number" to get your sending phone number.

**3. SendGrid API Keys (For Phase 3 - Email)**
*   Go to [sendgrid.com](https://sendgrid.com/) and create a free account.
*   On the left sidebar, navigate to **Settings > API Keys**.
*   Click **"Create API Key"** in the top right.
*   Give it a name (e.g., "TourneyPro App"), select **"Full Access"**, and click **Create & View**.
*   Copy the generated API Key immediately (it starts with `SG.`) as it will never be shown again.

## Open Questions
1. **Priority**: Do you agree with tackling Phase 1 first, or is there a specific feature (like WebSockets) you need immediately?
2. **Team Scoring**: For Team-based tournaments, should Teams simply aggregate the individual points of their players, or is it a specific format (e.g., Team A vs Team B consisting of 3 singles and 2 doubles matches)?
