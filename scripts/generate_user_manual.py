import base64
import os
import subprocess
import shutil

def get_base64_images():
    img_dir = os.path.abspath("docs/images")
    encoded = {}
    for fname in ["tournament_staff_management.png", "court_pin_login.png", "category_draw_publish_toggle.png", "tournament_desk_roster.png", "public_tournaments_list.png"]:
        p = os.path.join(img_dir, fname)
        if os.path.exists(p):
            with open(p, "rb") as f:
                encoded[fname] = base64.b64encode(f.read()).decode("utf-8")
    return encoded

def create_markdown_manual():
    md_content = """# 🏆 TourneyPro User Manual
### Simple Step-by-Step Guide for Tournament Directors, Umpires, Captains & Players

Welcome to **TourneyPro**! This user guide walks you through every action you can perform on the website. No technical setup is required—just open your browser on your computer, tablet, or mobile phone.

---

## 📋 Table of Contents
1. [User Roles Overview](#1-user-roles-overview)
2. [For Tournament Organizers & Directors](#2-for-tournament-organizers--directors)
   - [2.1 Appointing Tournament Staff & Umpires](#21-appointing-tournament-staff--umpires)
   - [2.2 Creating a 6-Digit PIN for Court Umpires](#22-creating-a-6-digit-pin-for-court-umpires)
   - [2.3 Publishing the Draw (Draft vs. Public)](#23-publishing-the-draw-draft-vs-public)
   - [2.4 Printing the Check-in Desk Roster PDF](#24-printing-the-check-in-desk-roster-pdf)
   - [2.5 Downloading Matches and Standings Sheets](#25-downloading-matches-and-standings-sheets)
3. [For Court Scorers & Chair Umpires](#3-for-court-scorers--chair-umpires)
   - [3.1 Logging in with a 6-Digit Court PIN](#31-logging-in-with-a-6-digit-court-pin)
   - [3.2 Entering Live Tennis Match Scores](#32-entering-live-tennis-match-scores)
   - [3.3 Fair Play Rule: Competitors Cannot Score Their Own Matches](#33-fair-play-rule-competitors-cannot-score-their-own-matches)
4. [For Team League Captains](#4-for-team-league-captains)
   - [4.1 Submitting Your Team Lineup](#41-submitting-your-team-lineup)
   - [4.2 The 15-Minute Deadline Rule](#42-the-15-minute-deadline-rule)
5. [For Players, Parents & Spectators](#5-for-players-parents--spectators)
   - [5.1 Registering for Tournaments](#51-registering-for-tournaments)
   - [5.2 Checking Match Times & Court Allocations](#52-checking-match-times--court-allocations)
   - [5.3 Viewing Live Scores & Brackets](#53-viewing-live-scores--brackets)
6. [Frequently Asked Questions (FAQ)](#6-frequently-asked-questions-faq)

---

## 1. User Roles Overview

| Role | What They Can Do |
| :--- | :--- |
| **🏆 Tournament Director (Organizer)** | Creates tournaments, manages divisions, appoints staff, generates umpire court PINs, toggles public draw publication, and prints the Desk Check-in Roster. |
| **👔 Tournament Staff (Manager / Official)** | Helps manage daily court schedules, handles delays, adjudicates walkovers, and oversees match play. |
| **⏱️ Court Scorer / Chair Umpire** | Scores matches live on court using a laptop, tablet, or phone (via normal login or instant 6-digit court PIN). |
| **🧢 Team Captain** | Submits player pairings for their team in league matches before the 15-minute pre-match deadline. |
| **🎾 Player / Athlete / Parent** | Registers for events, tracks personal match schedules on Order of Play, and views personal win/loss records. |
| **🌐 Spectator / Fan** | Browses public tournaments, tracks live scores ball-by-ball, and downloads official bracket PDFs. |

---

## 2. For Tournament Organizers & Directors

### 2.1 Appointing Tournament Staff & Umpires
As the tournament director, you can delegate scoring and court management to other registered users without sharing your account password.

![Tournament Staff Management](./images/tournament_staff_management.png)

#### Steps to Appoint Staff:
1. Log in and open your tournament dashboard (`/t/<slug>/manage`).
2. Click on the **🛡️ Staff & Umpires** tab.
3. Under **👤 Appoint Staff Member**:
   - **User Email or Username**: Type the username or email of the person you want to appoint.
   - **Staff Role**: Select `Manager` (schedules & scores), `Official / Referee` (rules & scoring), or `Scorer` (live score entry only).
   - **Assigned Court (Optional)**: E.g., `Court 1` or leave blank for all courts.
4. Click **➕ Appoint Staff Member**. Privileges are active immediately!

---

### 2.2 Creating a 6-Digit PIN for Court Umpires
If you have volunteer umpires, court attendants, or referees who do not have an account on TourneyPro, you can issue them a temporary 6-digit PIN.

#### Steps to Generate an Umpire PIN:
1. In the **🛡️ Staff & Umpires** tab, find the **⚡ Generate Court Access PIN** card.
2. Enter the **Assigned Court** (e.g., `Court 2` or `Center Court`).
3. Select the role (**Scorer**) and duration (e.g., **24 Hours (1 Day)**).
4. Click **⚡ Generate 6-Digit PIN**.
5. Give this 6-digit PIN to the umpire with the login link: `http://<your-domain>/t/<slug>/score-login`.

---

### 2.3 Publishing the Draw (Draft vs. Public)
While you are seeding players or balancing draws, keep brackets in **Draft** mode so players and spectators do not download incomplete draws.

![Category Draw Publish Toggle](./images/category_draw_publish_toggle.png)

#### How it Works:
- While in **Draft**, a `🔒 Draft Draw` badge is displayed. Public visitors cannot download the Draw PDF.
- Organizers and admins can preview the PDF draft at any time.
- To publish the draw:
  1. Open the Category view (`/t/<slug>/categories/<id>`).
  2. Click the green **📢 Publish Draw** button at the top header.
  3. The badge updates to `✅ Published`. The public can now immediately download the official Draw PDF!
  4. If changes are needed, click **🔒 Unpublish (Draft)** to take it down temporarily.

---

### 2.4 Printing the Check-in Desk Roster PDF
On tournament day, the registration desk needs a physical roster of all players, contact numbers, and payment details.

![Tournament Desk Roster Button](./images/tournament_desk_roster.png)

#### Steps to Download the Desk Roster:
1. Open the Tournament Hub (`/t/<slug>?view=bracket`).
2. Click the **🖨️ Desk Roster PDF** button in the top action bar.
3. A clean, formatted check-in sheet will open, ready to print for your physical registration desk.
4. *Privacy Notice:* This button is strictly visible only to tournament directors and platform admins.

---

### 2.5 Downloading Matches and Standings Sheets
On each category page, organizers have quick access to:
- **📄 Matches CSV**: Complete list of matches, courts, and scores for spreadsheets.
- **📊 Standings CSV**: Team points, set differentials, and qualification rankings.

---

## 3. For Court Scorers & Chair Umpires

### 3.1 Logging in with a 6-Digit Court PIN
Umpires do **not** need to create an account or remember a password to score matches.

![Court Scoring Mode PIN Login](./images/court_pin_login.png)

#### Steps for Umpires:
1. Open the browser on your phone or tablet and visit: `/t/<slug>/score-login`.
2. Enter the **6-digit Court PIN** (e.g., `849201`).
3. Tap **⚡ Unlock Court Scoring**. You are now logged into Court Scoring Mode!
4. When your shift ends, tap **Exit Court Scoring** to log out.

---

### 3.2 Entering Live Tennis Match Scores
1. In the Category or Order of Play view, tap on your match.
2. Tap **Report Score**.
3. Type the tennis score using standard formatting:
   - **Regular Sets**: `6-4, 6-3`
   - **Tiebreak Set**: `7-6(4), 6-4` *(loser's tiebreak points inside parentheses)*
   - **Super Tiebreak**: `6-4, 4-6, [10-7]`
4. Select the **Match Winner** and tap **Submit Result**.
5. *Simultaneous Score Notice:* If another official updated the score while your screen was open, the system will notify you. Simply refresh the page to view the latest score.

---

### 3.3 Fair Play Rule: Competitors Cannot Score Their Own Matches
To ensure sportsmanship:
- If you are a registered player in a match, the system automatically blocks you from recording or altering scores for that match.
- An independent umpire, official, or the director must report your match.

---

## 4. For Team League Captains

### 4.1 Submitting Your Team Lineup
In team championships, captains nominate which squad players will play in each individual match (rubber).

#### Steps to Submit Lineups:
1. Log in with your player account.
2. Open your team category page (`/t/<slug>/categories/<id>`).
3. Find your upcoming tie and click **Allot Lineup**.
4. Select Player 1 (and Player 2 for doubles) for each rubber. *(Opponent fields are protected and cannot be edited by your team)*.
5. Click **Save Lineups**.

---

### 4.2 The 15-Minute Deadline Rule
- **Important:** Lineups automatically lock **15 minutes before the scheduled match time**.
- Submit nominations early! If an emergency substitution is needed within 15 minutes, please contact the Chief Referee.

---

## 5. For Players, Parents & Spectators

![Public Tournaments Directory](./images/public_tournaments_list.png)

### 5.1 For Players & Parents
- **Online Registration:** Tap **✍️ Register Now** on any open tournament to enroll in singles or doubles divisions.
- **Find Match Times:** Tap **📋 Order of Play** at the top of the tournament page to view your court number, opponent, and estimated start time.
- **Player Dashboard:** Visit `/player/profile` to manage personal details and track your tournament history.

### 5.2 For Spectators & Fans
- **Live Scoreboards:** Follow active matches in real time as chair umpires input points from the court.
- **Official PDFs:** Download daily **Order of Play PDFs** and official **Draw PDFs** (once published by the director).

---

## 6. Frequently Asked Questions (FAQ)

#### Q: Why does the Draw PDF say it's unpublished?
**A:** The organizer is finalizing the draw. Once published, the download button will activate automatically.

#### Q: Can an umpire use their smartphone on court?
**A:** Yes! The `/score-login` interface is designed specifically for mobile touchscreens and tablets.

#### Q: What happens if a player gets injured during a match?
**A:** The umpire can select `Retired` in the score submission modal, and the opponent advances automatically.

#### Q: Can a player score their own match?
**A:** No. The system prevents competitors from submitting results for their own matches to maintain complete integrity.

---
*TourneyPro — Built for Tennis Tournament Directors, Umpires & Players.*
"""
    with open("docs/USER_MANUAL.md", "w") as f:
        f.write(md_content)
    print("Created docs/USER_MANUAL.md with relative image paths successfully!")

def create_html_and_pdf_manual(images):
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>TourneyPro User Manual</title>
<style>
    @page {{
        size: A4 portrait;
        margin: 12mm 14mm 12mm 14mm;
        @bottom-right {{
            content: "Page " counter(page);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            font-size: 8pt;
            color: #71717a;
        }}
        @bottom-left {{
            content: "TourneyPro Official User Manual";
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            font-size: 8pt;
            color: #a1a1aa;
        }}
    }}
    
    * {{
        box-sizing: border-box;
    }}
    
    body {{
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        color: #18181b;
        background: #ffffff;
        line-height: 1.4;
        font-size: 9.5pt;
        margin: 0;
        padding: 0;
    }}

    .cover {{
        text-align: center;
        padding: 16px 20px 14px;
        border-bottom: 2px solid #e4e4e7;
        margin-bottom: 16px;
    }}

    .cover-badge {{
        display: inline-block;
        background: #fef3c7;
        color: #b45309;
        font-weight: 700;
        font-size: 8pt;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        padding: 2px 8px;
        border-radius: 9999px;
        margin-bottom: 8px;
        border: 1px solid #fde68a;
    }}

    h1.title {{
        font-size: 22pt;
        font-weight: 800;
        color: #09090b;
        margin: 0 0 4px;
        letter-spacing: -0.02em;
    }}

    .subtitle {{
        font-size: 10.5pt;
        color: #52525b;
        margin: 0 0 8px;
        font-weight: 500;
    }}

    .meta {{
        font-size: 8pt;
        color: #71717a;
    }}

    h2 {{
        font-size: 13pt;
        font-weight: 700;
        color: #09090b;
        border-bottom: 1.5px solid #e4e4e7;
        padding-bottom: 3px;
        margin-top: 14px;
        margin-bottom: 8px;
        page-break-after: avoid;
    }}

    h3 {{
        font-size: 10.5pt;
        font-weight: 700;
        color: #18181b;
        margin-top: 10px;
        margin-bottom: 5px;
        page-break-after: avoid;
    }}

    p {{
        margin: 0 0 6px;
        color: #3f3f46;
    }}

    ul, ol {{
        margin: 0 0 8px;
        padding-left: 18px;
        color: #3f3f46;
    }}

    li {{
        margin-bottom: 3px;
    }}

    strong {{
        color: #09090b;
    }}

    .page-section {{
        page-break-after: always;
    }}

    .page-section:last-child {{
        page-break-after: avoid;
    }}

    .screenshot-card {{
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 6px;
        padding: 5px;
        margin: 8px 0 10px;
        page-break-inside: avoid;
        text-align: center;
    }}

    .screenshot-card img {{
        max-width: 92%;
        height: auto;
        border-radius: 4px;
        border: 1px solid #cbd5e1;
        box-shadow: 0 1px 5px rgba(0,0,0,0.06);
        display: block;
        margin: 0 auto;
    }}

    .caption {{
        font-size: 7.5pt;
        color: #64748b;
        margin-top: 4px;
        font-weight: 600;
        text-align: center;
    }}

    .role-table {{
        width: 100%;
        border-collapse: collapse;
        margin: 10px 0;
        font-size: 8.5pt;
        page-break-inside: avoid;
    }}

    .role-table th {{
        background: #f1f5f9;
        color: #0f172a;
        text-align: left;
        padding: 6px 10px;
        font-weight: 700;
        border-bottom: 2px solid #cbd5e1;
    }}

    .role-table td {{
        padding: 6px 10px;
        border-bottom: 1px solid #e2e8f0;
        vertical-align: top;
    }}

    .role-table tr:nth-child(even) td {{
        background: #f8fafc;
    }}

    .callout {{
        background: #eff6ff;
        border-left: 3.5px solid #3b82f6;
        padding: 7px 11px;
        border-radius: 4px;
        margin: 8px 0;
        page-break-inside: avoid;
        font-size: 8.5pt;
    }}

    .callout-title {{
        font-weight: 700;
        color: #1d4ed8;
        font-size: 8.5pt;
        margin-bottom: 2px;
    }}

    .callout-warning {{
        background: #fffbeb;
        border-left: 3.5px solid #f59e0b;
    }}

    .callout-warning .callout-title {{
        color: #b45309;
    }}

    .callout-success {{
        background: #f0fdf4;
        border-left: 3.5px solid #10b981;
    }}

    .callout-success .callout-title {{
        color: #047857;
    }}

    .step-list {{
        margin: 6px 0 8px;
    }}

    .step-item {{
        position: relative;
        padding-left: 22px;
        margin-bottom: 5px;
    }}

    .step-num {{
        position: absolute;
        left: 0;
        top: 0;
        width: 16px;
        height: 16px;
        background: #2563eb;
        color: #ffffff;
        font-size: 7pt;
        font-weight: 700;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        text-align: center;
        line-height: 16px;
    }}
</style>
</head>
<body>

<!-- PAGE 1: COVER & OVERVIEW -->
<div class="page-section">
    <div class="cover">
        <div class="cover-badge">Official TourneyPro Guide</div>
        <h1 class="title">🏆 TourneyPro User Manual</h1>
        <div class="subtitle">Complete Web Interface Guide for Tournament Directors, Umpires, Captains &amp; Players</div>
        <div class="meta">No technical setup required &bull; Works seamlessly on Desktop, Tablet &amp; Mobile &bull; Updated November 2026</div>
    </div>

    <h2>1. User Roles &amp; Capabilities Overview</h2>
    <p>TourneyPro provides an intuitive web experience designed specifically for each role in a tennis tournament:</p>

    <table class="role-table">
        <thead>
            <tr>
                <th style="width: 32%;">User Role</th>
                <th>Primary Web Capabilities</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td><strong>🏆 Tournament Director (Organizer)</strong></td>
                <td>Creates tournaments, manages divisions, appoints staff, generates umpire court PINs, toggles public draw publication, and prints the Desk Check-in Roster.</td>
            </tr>
            <tr>
                <td><strong>👔 Tournament Staff (Manager / Official)</strong></td>
                <td>Manages court queues, handles rain delays, updates scheduled times, adjudicates walkovers, and verifies scores.</td>
            </tr>
            <tr>
                <td><strong>⏱️ Court Scorer / Chair Umpire</strong></td>
                <td>Scores tennis matches live on court using a smartphone or tablet via standard account or instant <strong>6-digit Court PIN</strong>.</td>
            </tr>
            <tr>
                <td><strong>🧢 Team League Captain</strong></td>
                <td>Submits player nominations for their team's rubbers before the <strong>15-minute pre-match deadline</strong>.</td>
            </tr>
            <tr>
                <td><strong>🎾 Player / Athlete / Parent</strong></td>
                <td>Enters tournaments online, tracks upcoming matches on Order of Play, and views personal ranking statistics.</td>
            </tr>
            <tr>
                <td><strong>🌐 Public Spectator / Fan</strong></td>
                <td>Browses public tournaments, tracks live ball-by-ball scoreboards, and downloads official bracket PDFs.</td>
            </tr>
        </tbody>
    </table>

    <div class="callout callout-success">
        <div class="callout-title">💡 Pure Web Experience</div>
        Everything runs directly in your web browser. No apps to install. Works seamlessly on Chrome, Safari, Edge, Firefox, tablets, and smartphones.
    </div>
</div>

<!-- PAGE 2: FOR TOURNAMENT DIRECTORS - STAFF & PIN -->
<div class="page-section">
    <h2>2. For Tournament Organizers &amp; Directors</h2>

    <h3>2.1 Appointing Tournament Staff &amp; Umpires</h3>
    <p>As the tournament owner, you can authorize other registered users to score matches or manage courts without sharing your account password.</p>

    <div class="step-list">
        <div class="step-item"><div class="step-num">1</div>Log in and navigate to your tournament dashboard (<code>/t/&lt;slug&gt;/manage</code>).</div>
        <div class="step-item"><div class="step-num">2</div>Click on the <strong>🛡️ Staff &amp; Umpires</strong> tab in the navigation bar.</div>
        <div class="step-item"><div class="step-num">3</div>Under <strong>👤 Appoint Staff Member</strong>, enter the user's username or email (e.g., <code>testuser</code>).</div>
        <div class="step-item"><div class="step-num">4</div>Select their role: <strong>Manager</strong> (schedules &amp; scores), <strong>Official / Referee</strong> (rules &amp; scoring), or <strong>Scorer</strong> (live score entry only).</div>
        <div class="step-item"><div class="step-num">5</div>Click <strong>➕ Appoint Staff Member</strong>. Privileges are activated immediately!</div>
    </div>

    <div class="screenshot-card">
        <img src="data:image/png;base64,{images.get('tournament_staff_management.png', '')}" alt="Tournament Staff Management" />
        <div class="caption">Figure 1: Staff &amp; Umpires Tab — Appointing Staff Members and Generating 6-Digit Court PINs</div>
    </div>

    <h3>2.2 Creating a 6-Digit PIN for Court Umpires</h3>
    <p>When volunteer umpires or attendants do not have an account, generate an instant 6-digit court PIN:</p>
    <div class="step-list">
        <div class="step-item"><div class="step-num">1</div>Under <strong>⚡ Generate Court Access PIN</strong>, type the <strong>Assigned Court</strong> (e.g., <code>Court 2</code>).</div>
        <div class="step-item"><div class="step-num">2</div>Select the role (<strong>Scorer</strong>) and duration (e.g., <strong>24 Hours</strong>).</div>
        <div class="step-item"><div class="step-num">3</div>Click <strong>⚡ Generate 6-Digit PIN</strong>. Provide the 6-digit PIN and login link (<code>/t/&lt;slug&gt;/score-login</code>) to your umpire.</div>
    </div>
</div>

<!-- PAGE 3: FOR TOURNAMENT DIRECTORS - DRAW PUBLISHING -->
<div class="page-section">
    <h3>2.3 Publishing the Draw (Draft vs. Public)</h3>
    <p>When generating brackets, TourneyPro keeps draws in <strong>Draft</strong> mode to prevent premature public access while seeds and byes are finalized.</p>

    <div class="screenshot-card">
        <img src="data:image/png;base64,{images.get('category_draw_publish_toggle.png', '')}" alt="Category Draw Publish Toggle" />
        <div class="caption">Figure 2: Category Bracket Header — "📢 Publish Draw" toggle and "🔒 Draft Draw" badge</div>
    </div>

    <div class="callout callout-warning">
        <div class="callout-title">🔒 Draft Draw Protection</div>
        While in <strong>Draft Draw</strong>, public visitors who click "Export Draw PDF" receive a friendly restriction notice. Organizers can preview and test the PDF draft at any time.
    </div>

    <div class="step-list">
        <div class="step-item"><div class="step-num">1</div>Navigate to the category bracket: <code>/t/&lt;slug&gt;/categories/&lt;id&gt;</code>.</div>
        <div class="step-item"><div class="step-num">2</div>Review seeds, participant brackets, and byes.</div>
        <div class="step-item"><div class="step-num">3</div>Click the green <strong>📢 Publish Draw</strong> button at the top header.</div>
        <div class="step-item"><div class="step-num">4</div>The badge turns to <strong>✅ Published</strong>. The public can now immediately download the official Draw PDF!</div>
    </div>
</div>

<!-- PAGE 4: FOR TOURNAMENT DIRECTORS - DESK ROSTER & CSVS -->
<div class="page-section">
    <h3>2.4 Printing the Check-in Desk Roster PDF</h3>
    <p>For physical tournament registration desks, the director can export a confidential master roster with contact info and payment records.</p>

    <div class="screenshot-card">
        <img src="data:image/png;base64,{images.get('tournament_desk_roster.png', '')}" alt="Tournament Hub Desk Roster" />
        <div class="caption">Figure 3: Tournament Navigation Bar — "🖨️ Desk Roster PDF" visible exclusively to Directors</div>
    </div>

    <div class="callout callout-success">
        <div class="callout-title">🖨️ One-Click Desk Copy</div>
        On the Tournament Hub (<code>/t/&lt;slug&gt;?view=bracket</code>), click <strong>🖨️ Desk Roster PDF</strong>. A high-resolution, print-ready roster will open, ready to print for your physical registration desk.
    </div>

    <h3>2.5 Downloading Matches and Standings Sheets</h3>
    <p>On each category page, organizers have quick access to:</p>
    <ul>
        <li><strong>📄 Matches CSV:</strong> Complete list of matches, courts, and scores for spreadsheets.</li>
        <li><strong>📊 Standings CSV:</strong> Team points, set differentials, and qualification rankings.</li>
    </ul>
</div>

<!-- PAGE 5: FOR COURT SCORERS & UMPIRES -->
<div class="page-section">
    <h2>3. For Court Scorers &amp; Chair Umpires</h2>

    <h3>3.1 Logging in with a 6-Digit Court PIN</h3>
    <p>Umpires do not need a username or password. Simply use the 6-digit court PIN provided by the tournament director.</p>

    <div class="screenshot-card">
        <img src="data:image/png;base64,{images.get('court_pin_login.png', '')}" alt="Court Scoring Mode Login" />
        <div class="caption">Figure 4: Tablet-Optimized Court Scoring Mode Login at /t/&lt;slug&gt;/score-login</div>
    </div>

    <div class="step-list">
        <div class="step-item"><div class="step-num">1</div>Open your mobile or tablet browser and go to <code>/t/&lt;slug&gt;/score-login</code>.</div>
        <div class="step-item"><div class="step-num">2</div>Enter the <strong>6-digit Court PIN</strong> (e.g., <code>849201</code>).</div>
        <div class="step-item"><div class="step-num">3</div>Tap <strong>⚡ Unlock Court Scoring</strong>. You are immediately in live court scoring mode!</div>
    </div>

    <h3>3.2 Entering Tennis Scores</h3>
    <p>Tap on your match fixture and click <strong>Report Score</strong>. Enter scores using standard tennis syntax:</p>
    <ul>
        <li><strong>Standard 2-Set Match:</strong> <code>6-4, 6-3</code></li>
        <li><strong>Tiebreak Set:</strong> <code>7-6(4), 6-4</code> <em>(loser's tiebreak points inside parentheses)</em></li>
        <li><strong>Match Tiebreak (Decider):</strong> <code>6-4, 4-6, [10-7]</code></li>
        <li>Select the <strong>Match Winner</strong> and click <strong>Submit Result</strong>.</li>
    </ul>

    <div class="callout callout-warning">
        <div class="callout-title">⚖️ Anti-Conflict Rule</div>
        If you are playing in a match, the system automatically blocks you from recording or altering your own score. An independent official or director must record your match.
    </div>
</div>

<!-- PAGE 6: CAPTAINS, PLAYERS, SPECTATORS & FAQ -->
<div class="page-section">
    <h2>4. For Team League Captains</h2>
    <p>In team leagues, team captains nominate which players contest each individual rubber (Singles, Doubles 1, Doubles 2).</p>
    
    <div class="step-list">
        <div class="step-item"><div class="step-num">1</div>Log in with your player account and navigate to your team's division page.</div>
        <div class="step-item"><div class="step-num">2</div>Find your upcoming fixture and tap <strong>Allot Lineup</strong>.</div>
        <div class="step-item"><div class="step-num">3</div>Select your squad players for each rubber. <em>(Opponent fields are protected)</em>.</div>
        <div class="step-item"><div class="step-num">4</div>Click <strong>Save Lineups</strong>.</div>
    </div>

    <div class="callout callout-warning">
        <div class="callout-title">⏱️ 15-Minute Deadline Rule</div>
        Lineups automatically lock <strong>15 minutes prior to the scheduled fixture start time</strong>. Make sure to submit nominations early!
    </div>

    <h2>5. For Players, Parents &amp; Spectators</h2>
    <div class="screenshot-card">
        <img src="data:image/png;base64,{images.get('public_tournaments_list.png', '')}" alt="Public Tournaments Directory" />
        <div class="caption">Figure 5: Public Tournaments Directory — Browse events and follow live brackets</div>
    </div>

    <ul>
        <li><strong>Online Registration:</strong> Tap <strong>✍️ Register Now</strong> on any open tournament to enroll online.</li>
        <li><strong>Find Match Times:</strong> Tap <strong>📋 Order of Play</strong> at the top of the tournament page to view your court number and estimated start time.</li>
        <li><strong>Live Scores &amp; Downloads:</strong> Follow live scoreboards and download official <strong>Order of Play PDFs</strong> and <strong>Draw PDFs</strong> once published.</li>
    </ul>

    <h2>6. Frequently Asked Questions (FAQ)</h2>
    <p><strong>Q: Why does the Draw PDF say it's unpublished?</strong><br/>
    A: The organizer is finalizing the draw. Once published, the download button will activate automatically.</p>

    <p><strong>Q: Can an umpire use their smartphone on court?</strong><br/>
    A: Yes! The <code>/score-login</code> interface is designed specifically for mobile touchscreens and tablets.</p>

    <p><strong>Q: What if two umpires submit a score at the same time?</strong><br/>
    A: TourneyPro detects the conflict and asks you to tap Reload to verify the latest score.</p>
</div>

</body>
</html>
"""
    html_path = "docs/USER_MANUAL.html"
    with open(html_path, "w") as f:
        f.write(html_content)
    print("Created docs/USER_MANUAL.html with optimized pagination successfully!")

    # Compile to PDF using Google Chrome
    pdf_path = "docs/TourneyPro_User_Manual.pdf"
    chrome_bin = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    cmd = [
        chrome_bin,
        "--headless=new",
        f"--print-to-pdf={pdf_path}",
        "--no-pdf-header-footer",
        f"file://{os.path.abspath(html_path)}"
    ]
    print("Running Chrome print-to-pdf...")
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode == 0 and os.path.exists(pdf_path):
        size_kb = os.path.getsize(pdf_path) // 1024
        print(f"Generated {pdf_path} successfully! ({size_kb} KB)")
        shutil.copyfile(pdf_path, "docs/USER_MANUAL.pdf")
        print("Copied to docs/USER_MANUAL.pdf")
    else:
        print("Chrome PDF output:", res.stderr)

if __name__ == "__main__":
    create_markdown_manual()
    images = get_base64_images()
    create_html_and_pdf_manual(images)
