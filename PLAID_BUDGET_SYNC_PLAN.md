# Plaid Budget Sync — Planning Layer (Updated Implementation Plan)

**Developer:** krispix418@gmail.com
**Last Updated:** June 2026
**Status:** Pivoted — see below.

---

## Project Pivot

**Original goal:** Automate manual transaction entry into the Google Sheet household budget tracker via Plaid.

**New goal:** Use the Plaid project as a **planning layer** — auto-populating account balances and other financial data into the Google Sheet life hub. Budget *tracking* (transaction categorization, spend visibility, Chris/Jeff split) is being offloaded to **Origin Financial**, which handles that better out of the box with Partner Mode for couples.

**The Google Sheet stays the central life hub** — it's not going away. It just no longer needs to be a transaction inbox. Instead, Plaid feeds it structured financial *state* (balances, net worth inputs) that would otherwise be entered manually.

---

## Architecture (Updated)

```
Plaid API  →  Flask Server (Render)  →  Google Sheet (Apps Script)
(banks)       (/balances endpoint)       (Pay-Off Matrix, net worth tab)
```

Three components — same as before, but simpler scope:

1. **Flask Backend (Python, hosted on Render)** — calls Plaid `/accounts/balance/get`, returns current balances per linked account as JSON. Same security model as before (Google OIDC JWT auth).

2. **Google Apps Script** — calls `/balances`, writes balance values into specific cells in the Pay-Off Matrix tab (and eventually other planning sections).

3. **Pay-Off Matrix tab** — the primary target. Instead of manually entering card balances every month, the script auto-fills them on demand or on a schedule.

---

## What's Retired

The following original phases are **cancelled** — Origin Financial owns this now:

- ~~Inbox tab (transaction staging area)~~
- ~~Apps Script transaction filing logic~~
- ~~Card → Chris/Jeff/Living section routing~~
- ~~Duplicate prevention via transaction_id~~
- ~~Monthly tab auto-creation~~
- ~~Recurring bill pre-fill~~

The transaction sync code (`sync_transactions.py`, `plaid_fetch.py`) is kept for reference but is no longer the core of this project.

---

## What's Kept & Reused

| File | Status | Notes |
|------|--------|-------|
| `src/app.py` | ✅ Keep | Security model is solid — Google OIDC JWT auth, rate limiting, email allowlist. Swap `/transactions` for `/balances`. |
| `src/plaid_client.py` | ✅ Keep | Works as-is. Just needs Production env + credentials. |
| `src/sync_transactions.py` | 📦 Archive | Keep for reference, not actively used. |
| `src/plaid_fetch.py` | 📦 Archive | Same. |
| `render.yaml` | ✅ Keep | Deployment config unchanged. |
| `.env.template` | 🔧 Update | Add `PLAID_ACCESS_TOKEN`, switch `PLAID_ENV` to `production`. |

---

## Accounts to Connect (Unchanged)

| Account | Default Owner |
|---------|--------------|
| BoA | Chris |
| BILT Mastercard (now via Cardless/Bilt 2.0) | Chris — ⚠️ Plaid connectivity flaky as of Feb 2026, test carefully |
| AMEX Gold | Chris |
| SoFi Checking | Chris |
| Citi | Chris |
| Apple Card | Jeff |
| Chase Sapphire (CSP) | Jeff |
| Venmo (Chris) | Chris — coverage may vary |
| Venmo (Jeff) | Jeff — coverage may vary |

---

## Phase Roadmap (Updated)

### ✅ Phase 1 — Plaid Setup (COMPLETE)
- Plaid developer account created
- Sandbox credentials in 1Password
- Flask server skeleton built with Google OIDC security model

### ▶️ Phase 2 — Switch to Production & Connect Real Accounts (NEXT)
- Get Production credentials from Plaid dashboard (dashboard.plaid.com → Production section)
- Update `.env.template` and 1Password entry: `PLAID_ENV=production`, use Production secret
- Build or use Plaid Link to connect real bank accounts and generate access tokens
- Store access tokens securely (Render env vars, one per institution or one multi-account item)
- Verify connections in Plaid dashboard

### Phase 3 — `/balances` Endpoint
- Replace `/transactions` with `/balances` in `app.py`
- Call Plaid `/accounts/balance/get` for all linked access tokens
- Return JSON: `{ "accounts": [{ "name": "AMEX Gold", "balance": 1234.56, "account_id": "..." }] }`
- Add account → friendly name mapping (config or env var)
- Test locally, deploy to Render

### Phase 4 — Apps Script: Pay-Off Matrix Auto-Fill
- Write Apps Script that calls `/balances` (with Google OIDC token)
- Map account names → specific cells in the Pay-Off Matrix tab
- Add a "Refresh Balances" button to the Sheet
- Optional: add a daily trigger for automatic refresh

### Phase 5 — Additional Planning Automations (Future)
- **Net worth snapshot tab** — write monthly balance snapshots for historical tracking
- **Savings runway calc** — pull checking/savings balances, compute months of runway
- Other planning use cases TBD based on what's painful to update manually

---

## Open Questions (Follow-up Before Phase 4)

These need answers before building the Apps Script Pay-Off Matrix integration:

1. **Pay-Off Matrix structure** — what does it look like exactly? Columns, rows, which cells map to which card? Screenshot or description needed to target the right cells.
2. **Card list to auto-fill** — confirming the exact list of cards and whether BILT should be included given its current Plaid flakiness.
3. **BILT status check** — test whether Plaid (via MX or Finicity fallback) can connect to Bilt 2.0 / Cardless before committing to including it.

---

## Key Reminders

- **Never commit secrets** — `.env`, access tokens, credentials → `.gitignore`
- **Plaid Production** = real account data, free up to 100 connected items
- **BILT heads-up** — Wells Fargo partnership ended Feb 2026; Bilt is now on Cardless. Plaid connectivity has been reported as spotty across all budgeting apps. Test early.
- **Render cold start** — free tier spins down after inactivity; first daily trigger may take ~30s
- **Origin Financial** handles transaction tracking for Chris + Jeff. This project does NOT need to touch transactions anymore.

---

## Next Action

Begin **Phase 2**: log into Plaid dashboard, grab Production credentials, update 1Password and `.env.template`, then connect the first real account to verify the Production setup works end-to-end.
