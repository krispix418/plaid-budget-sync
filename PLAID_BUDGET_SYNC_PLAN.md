# Plaid Budget Sync — Implementation Plan & Claude Code Handoff

**Developer:** krispix418@gmail.com
**Workflow:** Planned in Claude.ai → implementing in Claude Code → debugging back in Claude.ai
**Status:** Phase 1 complete (Plaid account + sandbox credentials). Starting Phase 2.

---

## Project Goal

Automate manual transaction entry into an existing Google Sheets household budget tracker shared between Chris and Jeff. Plaid pulls transactions from linked accounts → a backend server exposes them → Google Apps Script writes them into an Inbox tab in the sheet → user reviews/assigns → transactions get filed into the correct section of the current month's tab.

**This replaces the tedious manual entry of every expense across multiple cards.**

---

## Architecture

```
Plaid API  →  Flask Server (Render)  →  Google Sheet (Apps Script + Inbox tab)
(banks)       (/transactions endpoint)   (review, assign, file)
```

Three components:

1. **Flask Backend (Python, hosted free on Render)** — handles all Plaid communication securely. API keys live here as environment variables, never in the browser or sheet. Exposes `GET /transactions` returning current-month transactions as JSON.

2. **Google Apps Script (lives in the sheet)** — calls the Flask server, writes transactions to the Inbox tab, handles auto-tab-creation and filing.

3. **Inbox Tab (staging area in the sheet)** — where new transactions land for review before being filed. The only thing the user/Jeff ever touches.

---

## Key Decisions Made

| Decision | Choice |
|----------|--------|
| Scope | **Current month only** — no historical backfill |
| Month tab creation | **Option B: script auto-creates** the new month tab on the 1st by duplicating previous month's structure |
| Recurring bills | **Pre-filled automatically** from previous month; user edits amounts freely, automation never overwrites |
| Crossover transactions | Inbox **dropdown** for Chris/Jeff/Living — user overrides default before filing |
| Transaction writes | Plaid transactions **only ever write to the Inbox tab** — manual edits elsewhere are always safe |
| Duplicate prevention | Plaid `transaction_id` stored in hidden column |

---

## The Sheet Structure (Context)

Each monthly tab (e.g. "April Spending Tracker") has 4 side-by-side sections:

- **Recurring Bills** (cols A–F): fixed monthly expenses, pre-filled by script
- **Living Budget** (cols G–M): shared household spending — Date | Description | Tag | Amount | Payback flags | Card Used
- **Chris Allowance** (cols N–U): Chris's personal spending, same structure
- **Jeff Allowance** (cols V–AC): Jeff's personal spending, same structure

Plus a **Pay-Off Matrix** at the top (balances per card across BoA/SoFi accounts) — stays manual.

**Note:** Formulas reference across tabs (e.g. `'DD Strategy'!J4`), so tab duplication must preserve formulas correctly — flagged for Phase 5 testing.

---

## Accounts to Connect

| Account | Default Section |
|---------|----------------|
| BoA | Chris Allowance |
| BILT Mastercard (via Wells Fargo) | Chris Allowance |
| AMEX Gold | Chris (floats to Living for shared) |
| SoFi Checking | Chris Allowance |
| Citi | Chris Allowance |
| Apple Card | Jeff Allowance |
| Chase Sapphire (CSP) | Jeff Allowance |
| Venmo (Chris) | Chris — coverage may vary, test |
| Venmo (Jeff) | Jeff — coverage may vary, test |

**Card → Section mapping** handles ~85% automatically; crossover handled via Inbox dropdown.

Instacart and Amazon Prime are merchants, not accounts — they appear on whatever card is linked.

---

## Inbox Tab Layout

| Date | Merchant | Tag | Amount | Card | Who | Status |
|------|----------|-----|--------|------|-----|--------|
| Apr 2 | Food Cellar | Groceries/Food | $38.14 | AMEX Gold | Living ▾ | Pending ▾ |
| Apr 3 | Sweetleaf Coffee | Eating Out | $6.34 | BILT | Chris ▾ | Pending ▾ |

- **Who** dropdown: Chris / Jeff / Living (pre-filled by card)
- **Tag** dropdown: matches existing category tags (pre-filled from Plaid category)
- **File It** button moves approved rows into the correct section of current month tab

---

## Plaid Transaction Fields Used

| Plaid field | Maps to |
|-------------|---------|
| `date` | Date column |
| `merchant_name` | Description / merchant |
| `amount` | Amount column |
| `account_id` | Determines Card Used + Who |
| `category` | Pre-fills Tag (user verifies) |
| `transaction_id` | Duplicate prevention |

---

## Tech Stack

- **Backend:** Python (Flask)
- **Hosting:** Render.com (free tier)
- **Plaid SDK:** `plaid-python` (official)
- **Sheet layer:** Google Apps Script (JavaScript)
- **Scheduling:** Apps Script daily trigger OR manual sync button
- **Secrets:** Render environment variables + local `.env` (gitignored)

---

## Phase Roadmap

### ✅ Phase 1 — Plaid Setup (COMPLETE)
- Plaid developer account created
- Sandbox credentials obtained (client_id + sandbox secret)
- Environment: `sandbox` for building/testing

### ▶️ Phase 2 — Flask Server (NEXT — START HERE)
Build the backend:
- Project structure + virtualenv + `requirements.txt`
- `.env` file for Plaid credentials (gitignored)
- Plaid Link flow to connect accounts (generates access tokens)
- `GET /transactions` endpoint returning current-month transactions as JSON
- Test locally against Plaid Sandbox
- Deploy to Render with environment variables

### Phase 3 — Google Apps Script
- Auto-tab creation on the 1st (duplicate prior month, pre-fill recurring bills)
- Inbox tab creation with dropdowns (Who / Tag)
- Fetch transactions from Flask server → write to Inbox
- Daily trigger + manual sync button

### Phase 4 — Filing Logic
- "File It" action: move Inbox rows → correct section of current month tab
- Card → section default mapping
- Duplicate prevention via transaction_id

### Phase 5 — Testing & Polish
- Connect real accounts (Plaid Development environment)
- Category mapping table (Plaid categories → your tags)
- Verify tab duplication preserves cross-tab formulas
- Test Venmo + BILT connectivity
- Jeff walkthrough

---

## Important Reminders

- **Never commit secrets** — `.env`, credentials → `.gitignore`
- **Sandbox first** — fully test with fake data before connecting real accounts
- **Plaid environments:** Sandbox (fake/free) → Development (real, free ≤100 items) → Production (not needed)
- **Render cold start:** free tier spins down after inactivity, first daily sync may take ~30s

---

## Next Action

Begin **Phase 2**: set up the Flask project structure and build the `/transactions` endpoint, tested against Plaid Sandbox. See the companion Claude Code kickoff prompt.
