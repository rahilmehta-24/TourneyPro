# TourneyPro — Model Context Protocol Specification (MCP.md)

**Document Status:** Approved  
**Source of Truth:** Inherits from [`AUTH.md`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/AUTH.md), [`API.md`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/API.md), [`DATABASE.md`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/DATABASE.md), and [`AGENTS.md`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/AGENTS.md)  
**Protocol Version:** MCP 2024-11-05 Specification  
**Architecture:** Model Context Protocol (MCP) Server for TourneyPro Developer Tooling & Automation  
**Last Updated:** October 2026  

---

## 1. Overview & Architectural Role

The **TourneyPro Model Context Protocol (MCP) Server** bridges large language models (LLMs), autonomous AI agents (such as Antigravity, Claude Desktop, Cursor), and the TourneyPro application layer. Through standard JSON-RPC 2.0 messages, AI agents can inspect tournament draws, analyze court bottlenecks, report live match scores, and execute database diagnostics without manual UI clicking.

```
┌─────────────────────────────────┐
│     AI Agent / IDE Host         │
│ (Antigravity / Claude / Cursor) │
└────────────────┬────────────────┘
                 │ JSON-RPC 2.0 (stdio or SSE)
                 ▼
┌─────────────────────────────────┐
│     TourneyPro MCP Server       │
│  - Tool Registry & Dispatcher   │
│  - Resource Exposer             │
│  - Authentication & BOLA Check  │
└────────────────┬────────────────┘
                 │ Python / ORM
                 ▼
┌─────────────────────────────────┐
│    TourneyPro Service Layer     │
│ (Format Engine, Scheduler, DB)  │
└─────────────────────────────────┘
```

---

## 2. Server Configuration & Setup

### 2.1 Stdio Transport Configuration
To integrate TourneyPro MCP tools into your local agent environment, add the following block to your `mcp_config.json`:

```json
{
  "mcpServers": {
    "tourneypro": {
      "command": "/Users/rahilmehta24/VS_Code/Projects/TourneyPro/venv/bin/python",
      "args": [
        "-m",
        "scripts.mcp_server"
      ],
      "env": {
        "FLASK_APP": "run.py",
        "DATABASE_URL": "sqlite:///instance/tournaments.db",
        "SUPERADMIN_USERNAME": "superadmin"
      }
    }
  }
}
```

---

## 3. Tool Registry Specifications

The TourneyPro MCP server exposes 10 specialized agent tools:

### 3.1 `tourneypro_list_tournaments`
* **Description:** Lists all active or past tournaments with summary statistics.
* **Input Schema:**
  ```json
  {
    "type": "object",
    "properties": {
      "status": {
        "type": "string",
        "enum": ["all", "setup", "in_progress", "completed"],
        "default": "all"
      },
      "limit": { "type": "integer", "default": 20 }
    }
  }
  ```
* **Output:** JSON array of tournaments with IDs, names, slugs, statuses, and category counts.

---

### 3.2 `tourneypro_get_tournament_details`
* **Description:** Retrieves complete tournament hierarchy including categories, participants, court allocations, and date windows.
* **Input Schema:**
  ```json
  {
    "type": "object",
    "properties": {
      "url_slug": { "type": "string", "description": "Unique tournament slug" }
    },
    "required": ["url_slug"]
  }
  ```

---

### 3.3 `tourneypro_create_tournament`
* **Description:** Provisions a new tournament container with multi-day calendar and court parameters.
* **Input Schema:**
  ```json
  {
    "type": "object",
    "properties": {
      "name": { "type": "string" },
      "url_slug": { "type": "string" },
      "game_info": { "type": "string", "default": "Lawn Tennis" },
      "num_courts": { "type": "integer", "default": 2 },
      "start_date": { "type": "string", "format": "date" },
      "end_date": { "type": "string", "format": "date" },
      "court_operating_start": { "type": "string", "default": "08:00" },
      "court_operating_end": { "type": "string", "default": "20:00" }
    },
    "required": ["name", "url_slug"]
  }
  ```

---

### 3.4 `tourneypro_generate_draw`
* **Description:** Generates mathematical brackets for a category based on registered participants.
* **Input Schema:**
  ```json
  {
    "type": "object",
    "properties": {
      "category_id": { "type": "integer" },
      "format": {
        "type": "string",
        "enum": ["single_elimination", "doubles_elimination", "round_robin", "group_stage"]
      }
    },
    "required": ["category_id"]
  }
  ```
* **Behavior:** Computes power-of-2 geometry, balances Byes, places top seeds, and creates initial round fixtures.

---

### 3.5 `tourneypro_reset_draw`
* **Description:** Safely resets a category bracket back to setup phase, purging fixtures while preserving registered participants.
* **Input Schema:**
  ```json
  {
    "type": "object",
    "properties": {
      "category_id": { "type": "integer" },
      "confirmation": { "type": "boolean", "description": "Must be true to prevent accidental resets" }
    },
    "required": ["category_id", "confirmation"]
  }
  ```

---

### 3.6 `tourneypro_report_match_score`
* **Description:** Records match score, handles tiebreak/summation rules, and advances winner to downstream fixture.
* **Input Schema:**
  ```json
  {
    "type": "object",
    "properties": {
      "match_id": { "type": "integer" },
      "score1": { "type": "string" },
      "score2": { "type": "string" },
      "winner_id": { "type": "integer" },
      "action_type": {
        "type": "string",
        "enum": ["complete_match", "live_score", "pending"],
        "default": "complete_match"
      }
    },
    "required": ["match_id"]
  }
  ```
* **Validation:** Enforces `check_match_progression_allowed()` and validates BOLA ownership.

---

### 3.7 `tourneypro_get_court_schedule`
* **Description:** Inspects Order of Play court schedule for potential player clashes, rest violations, or progression lock issues.
* **Input Schema:**
  ```json
  {
    "type": "object",
    "properties": {
      "tournament_id": { "type": "integer" },
      "target_date": { "type": "string", "format": "date" }
    },
    "required": ["tournament_id"]
  }
  ```

---

### 3.8 `tourneypro_lookup_player`
* **Description:** Retrieves career stats, win rate, ranking points, and historical finishes for an athlete.
* **Input Schema:**
  ```json
  {
    "type": "object",
    "properties": {
      "player_id": { "type": "integer" },
      "search_query": { "type": "string" }
    }
  }
  ```

---

### 3.9 `tourneypro_sync_database_schema`
* **Description:** Executes non-destructive schema reconciliation inspecting PostgreSQL/SQLite against SQLAlchemy models.
* **Input Schema:**
  ```json
  {
    "type": "object",
    "properties": {
      "dry_run": { "type": "boolean", "default": false }
    }
  }
  ```

---

### 3.10 `tourneypro_run_diagnostics`
* **Description:** Runs Ruff linter and the 72-test automated unit test suite, returning pass/fail metrics.
* **Input Schema:**
  ```json
  {
    "type": "object",
    "properties": {}
  }
  ```

---

## 4. MCP Resources

The MCP server exposes direct URI resources for agent context ingestion:

* `tourneypro://tournaments/{slug}`: Read-only Markdown summary of tournament structure.
* `tourneypro://categories/{id}/bracket`: Visual ASCII representation of current bracket state.
* `tourneypro://schedule/{slug}/order-of-play`: Current daily schedule matrix.
* `tourneypro://players/{id}/stats`: Athlete career summary card.

---

## 5. Security & Permission Scoping

1. **Authentication:** MCP server sessions running in administrative mode map to the local superadmin account.
2. **Safety Gates:** Critical actions (bracket resets, schema alterations) require explicit boolean confirmations (`confirmation: true`).
3. **Rollback Guarantee:** All mutating database queries are wrapped in try-catch blocks with explicit `db.session.rollback()` on exception.
