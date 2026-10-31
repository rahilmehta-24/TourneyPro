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
