# TourneyPro — Quality Assurance & Testing Strategy (TESTING.md)

**Document Status:** Approved  
**Source of Truth:** Inherits from [`INTEGRATIONS.md`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/INTEGRATIONS.md), [`ARCHITECTURE.md`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/ARCHITECTURE.md), and [`FEATURES.md`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/FEATURES.md)  
**Test Framework:** Python Standard Library `unittest` (compatible with `pytest`)  
**Active Test Suite:** 72 Automated Unit & Integration Tests Passing (12.2s execution time)  
**Last Updated:** October 2026  

---

## 1. Testing Philosophy & Standards

To guarantee enterprise-grade stability during high-stakes tournament finals, TourneyPro enforces three core testing tenets:

1. **Real Database Isolation:** Unit and integration tests avoid fragile, unrealistic database mocks. Every test suite provisions an isolated, temporary SQLite database file via `tempfile.mkstemp()`, builds tables via `db.create_all()`, and executes live queries, transactions, and cascades.
2. **Deterministic Mathematical Verification:** Bracket geometries, power-of-2 Bye allocations, rubber summation math ($T=7$), and cumulative group standings are asserted with exact expected numeric outputs.
3. **Strict Regression Gates:** No code is committed to `main` or `uat` without 100% pass rates across all test suites and zero linter warnings.

---

## 2. Test Suite Inventory

The automated test suite spans 7 specialized test modules covering 72 distinct test scenarios:

```
tests/
├── test_team_league.py              # 18 tests (49 KB) - Group stage, rubber math, drafts, schedulers
├── test_security_remediation.py     # 4 tests (5 KB)   - BOLA / IDOR protection, JWT tokens
├── test_migrations.py               # 6 tests (3.4 KB) - Alembic migration integrity, SQLite batch mode
├── test_draw_pdf_export.py          # 12 tests (23 KB) - Bracket PDF rendering, ETag caching
├── test_order_of_play_pdf_export.py # 10 tests (16 KB) - Daily court schedule PDF generation
├── test_participants_pdf_export.py  # 10 tests (16.5 KB)- Player rosters & check-in PDF exports
└── test_admin_approval_box.py       # 12 tests (16 KB) - Registration verification & payment transitions
```

### 2.1 Detailed Module Breakdown

#### 2.1.1 `test_team_league.py`
Comprehensive verification of the Group Stage Team League engine:
* `test_01_rubber_scoring_default_t7`: Validates summation rule ($G_1 + G_2 = 7$) and 3–3 tiebreak deciding game.
* `test_02_rubber_scoring_dynamic_t5_and_t9`: Tests alternative game totals.
* `test_03_team_fixture_status_first_to_11`: Validates 21-game total and first-to-11 tie win condition.
* `test_04_auto_create_teams_mode_b`: Verifies balanced distribution of 1 player from each of the 5 skill tiers into teams.
* `test_05_fixture_generation_with_3_rubbers`: Validates round-robin team tie generation and child rubber creation.
* `test_06_head_to_head_group_standings`: Verifies Head-to-Head is the primary tiebreaker for equal wins.
* `test_07_knockout_unified_ranking_and_seeding`: Validates group promotion into knockout stages.
* `test_08_manual_chit_draw_duplicate_prevention`: Proves Mode A blocks duplicate player drafting.
* `test_09_scheduler_respects_group_start_timing`: Verifies court scheduler synchronizes child rubbers with group session hours.
* `test_14_rubber_reporting_summation_rule`: Enforces HTTP report endpoint rejection of non-7 score sums.
* `test_15_walkover_and_retirement_remainder_scoring`: Verifies mid-match retirement awards all remaining unplayed games to opposition.
* `test_16_knockout_guard_against_pending_group_matches`: Proves start-knockout action blocks bracket generation while pool matches remain pending.
* `test_18_order_of_play_displays_full_scoreline`: Verifies completed team fixtures display complete scoreline (e.g. `17 – 4`).

#### 2.1.2 `test_security_remediation.py`
* `test_api_report_match_bola_protection`: Proves Admin 2 cannot report or modify matches in Admin 1's tournament.
* `test_web_controller_ownership_guard`: Asserts HTTP 403 on unauthorized cross-organizer mutations.
* `test_jwt_bearer_token_validation`: Verifies rejection of expired or malformed bearer tokens.

#### 2.1.3 `test_migrations.py`
* Validates that Alembic migration revisions upgrade cleanly.
* Verifies SQLite batch mode alterations (`render_as_batch=True`).
* Confirms column presence for newly introduced scheduling fields.

#### 2.1.4 `test_draw_pdf_export.py` & PDF Suites
* Verifies vector PDF byte generation for brackets, orders of play, and rosters.
* Tests HTTP 304 Not Modified ETag caching responses.

---

## 3. Test Fixture & Isolation Architecture

Every test suite uses an isolated temporary database lifecycle:

```python
class IsolatedTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create unique temporary SQLite file
        cls.db_fd, cls.db_path = tempfile.mkstemp(suffix='.db')
        os.close(cls.db_fd)

        class TestConfig:
            TESTING = True
            SECRET_KEY = 'test-secret'
            SQLALCHEMY_DATABASE_URI = f'sqlite:///{cls.db_path}'
            SQLALCHEMY_TRACK_MODIFICATIONS = False
            WTF_CSRF_ENABLED = False

        cls.app = create_app(TestConfig)
        cls.app_context = cls.app.app_context()
        cls.app_context.push()
        db.create_all()

    @classmethod
    def tearDownClass(cls):
        db.session.remove()
        cls.app_context.pop()
        if os.path.exists(cls.db_path):
            os.remove(cls.db_path)  # Clean up temp file
```

---

## 4. Test Execution Commands

### 4.1 Run Entire Test Suite
```bash
python -m unittest discover tests -v
```
*Expected Output:*
```text
Ran 72 tests in 12.219s
OK
```

### 4.2 Run Specific Test File
```bash
python -m unittest tests/test_team_league.py -v
```

### 4.3 Run Single Test Case
```bash
python -m unittest tests.test_team_league.TeamLeagueTestCase.test_01_rubber_scoring_default_t7
```

### 4.4 Run Test Suite with Pytest
```bash
PYTHONPATH=. pytest
```

---

## 5. Continuous Integration (CI/CD Quality Gate)

Every push and Pull Request to `main` and `uat` triggers the GitHub Actions workflow [`.github/workflows/ci.yml`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/.github/workflows/ci.yml):

```yaml
name: CI & Quality Gate
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: |
          pip install --upgrade pip
          pip install -r requirements.txt
      - name: Lint with Ruff
        run: ruff check .
      - name: Run Test Suite
        run: python -m unittest discover tests -v
```
All pull requests require passing status checks before merging.

---

## 6. Mobile Responsiveness & Viewport Quality Assurance

To ensure zero regressions across mobile platforms, UI enhancements undergo systematic validation:

* **Viewport Range Matrix:** Audited across small mobile (`320px` to `375px`, iPhone SE), modern standard mobile (`390px` to `430px`, iPhone 14/15/16, Google Pixel, Galaxy S24), and tablet (`768px` to `992px`, iPad).
* **Safe-Area Verification:** Confirms notch, dynamic island, and bottom gesture bar spacing using `viewport-fit=cover` and `env(safe-area-inset-bottom)`.
* **Touch Event Validation:** Confirms `touchstart`, `touchmove`, `touchend` listeners pan the bracket canvas smoothly without altering horizontal SVG connector alignments.
* **Input Usability Check:** Confirms `font-size: 16px !important;` prevents iOS Safari auto-zoom on form focus, and `inputmode="numeric"` engages numeric keypads.
* **Desktop Regression Check:** Validates desktop screens (`> 992px`) maintain pixel-perfect layout, multi-column grids, and centered modal dialogs.

