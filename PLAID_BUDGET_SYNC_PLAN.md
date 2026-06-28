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

## Decision Note — 2026-06-28 (Redundancy check + sequencing)

Revisited "is this project redundant now that Origin is in the picture?" Verdict: **not redundant, but re-scope and pressure-test before building Phase 4.**

- **Origin makes the raw *data* redundant** — it already aggregates every card + bank balance via Plaid on one screen. The generic "what do I owe / what cash do I have" view is free in Origin.
- **Origin does NOT do the Pay-Off Matrix reconciliation** — matching each card balance to the *funded space* earmarked to pay it ("BILT balance = X, SoFi Checking-for-bills = Y, am I covered?"). That card→space matching is the project's actual IP and the only thing worth automating.
- **Sequencing decision:** before building the Apps Script auto-fill (Phase 4), spend **one month** using Origin's accounts screen at month-end. Measure how much manual reconciliation *actually* remains. If it shrinks to "glance + 5 min," skip the build. If the reconciliation is still painful, build *only that layer* — now with a precise spec instead of building blind.
- **Open Question #1 (Pay-Off Matrix structure) is now answered** — the monthly Spending Tracker tabs contain a "PAY-OFF MATRIX" block: columns are `Card Used | Who? | Recurring Bills | Living | Chris Allowance | Jeff Allowance | ST Savings | Totals | PB Amt | Paid Back? | Paid?`, plus a side block `NEED TO PAY OFF (per card) | BoA | Sofi Savings (Extra) | Sofi Checking (Living) | CASH AVAIL`. That side block is the auto-fill target.

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

## Plaid Products Needed (Bare Minimum)

Now that this is a balances/planning layer (Origin owns transactions), only **two** Plaid products are required:

| Product | Endpoint | What it gives us |
|---------|----------|------------------|
| **Balance** | `/accounts/balance/get` | Current + available balance on any depository (checking/savings) or credit account. Core of net-worth / runway inputs. |
| **Liabilities** | `/liabilities/get` | Richer card data — statement balance, minimum payment, due date, APR, last payment. This is what makes the Pay-Off Matrix actually useful (vs. just current balance). |

**Not needed:** Transactions (Origin owns it), Auth (routing #s — only for moving money), Investments (no brokerage accounts in scope).

> One institution login = one Plaid **Item** = one access token covering *all* accounts under it. Store **one token per institution**, not per card (e.g. both Chase cards come back under a single Chase token).

---

## Accounts to Connect — Connectivity Tiering

Tiered by how reliably Plaid actually connects. Build the bare-minimum set first (Tier 1), treat Tier 2 as "nice if it connects, don't depend on it."

### ✅ Tier 1 — Solid (build on these)

| Account | Owner | Pull | Notes |
|---------|-------|------|-------|
| BoA (checking/savings) | Chris | Balance | OAuth, connects cleanly. One token covers checking + savings. |
| SoFi Checking | Chris | Balance | Generally reliable. |
| Chase Prime Visa | Chris | Liabilities | All 3 Chase cards under **one** Chase connection/token. |
| Chase Instacart Mastercard | Chris | Liabilities | Same Chase Item. |
| Chase Sapphire Preferred (CSP) | Jeff | Liabilities | Same Chase Item — ownership split, one token. |
| AMEX Gold | Chris | Liabilities | OAuth, solid. |
| Citi | Chris | Liabilities | OAuth, generally solid. |

### ⚠️ Tier 2 — Finicky / known gaps (test before depending on)

| Account | Owner | Pull | Risk |
|---------|-------|------|------|
| Apple Card | Jeff | Liabilities | **Biggest gap.** Apple Card / Goldman has historically had *no* Plaid support (manual export only), and the Goldman partnership has been winding down. Don't count on it. |
| BILT Mastercard (Cardless / Bilt 2.0) | Chris | Liabilities | Wells Fargo partnership ended Feb 2026; now on Cardless. Plaid connectivity reported spotty across budgeting apps. Test early. |
| Venmo (Chris) | Chris | Balance | Coverage varies. |
| Venmo (Jeff) | Jeff | Balance | Coverage varies. |

> **Note on Fidelity:** not in scope, but flagged for reference — Plaid *can* connect to Fidelity, though investment accounts are often finicky. Revisit only if a brokerage/net-worth use case comes up later.

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

## Phase 4 — Auto-Fill Spec (Draft, pre-build)

**Status:** Drafted 2026-06-28, *not* greenlit. Gated on the one-month measurement (see Decision Note). Build only if month-end reconciliation stays painful.

**Auto-fill target:** the `NEED TO PAY OFF (per card)` side block on the monthly Spending Tracker tabs. These columns are the **cash sources** available to cover card balances — so the target is almost entirely **Balance** pulls, not Liabilities.

| Sheet cell (side block) | Plaid source | Product | Pull | Notes |
|-------------------------|--------------|---------|------|-------|
| **BoA** | BoA depository account | Balance | `available` | ⚠️ Confirm: is this BoA *checking* or *savings*? One BoA token covers both — need to target the right account_id. |
| **Sofi Savings (Extra)** | SoFi savings account | Balance | `available` | ⚠️ Tier 1 list only had "SoFi Checking" — confirm a SoFi *savings* account exists under the same SoFi item. |
| **Sofi Checking (Living)** | SoFi checking account | Balance | `available` | Same SoFi token as savings. |
| **CASH AVAIL** | *(derived)* | — | — | Almost certainly a **sheet formula** (sum of the above), not a Plaid pull. Confirm before wiring. |

**Implication for product priority:** earlier I leaned on Liabilities for the card data — but this specific auto-fill target is **Balance-only**. Liabilities (card statement balances) is only needed if the *main* matrix block (`Card Used | … | PB Amt | Paid?`) also gets auto-filled. **Open question below.**

---

## Open Questions (Follow-up Before Phase 4)

These need answers before building the Apps Script Pay-Off Matrix integration:

1. ~~**Pay-Off Matrix structure**~~ — ✅ **Answered** (see Decision Note 2026-06-28). Target = `NEED TO PAY OFF (per card)` side block; mapping drafted in the Auto-Fill Spec above.
2. **Cash-side account IDs** — confirm exactly which accounts back `BoA` (checking vs savings) and whether a `SoFi Savings (Extra)` account exists separate from checking. Needed to target the right `account_id`s.
3. **Is `CASH AVAIL` derived or pulled?** — confirm it's a sheet formula, not a Plaid value.
4. **Does the main matrix block also need auto-fill?** — if yes, that's where Liabilities (card statement balances) comes back into scope. If the side cash block is the *only* target, Liabilities can be dropped entirely.
5. **Card list to auto-fill** — confirming the exact list of cards and whether BILT should be included given its current Plaid flakiness.
6. **BILT status check** — test whether Plaid (via MX or Finicity fallback) can connect to Bilt 2.0 / Cardless before committing to including it.

---

## Key Reminders

- **Never commit secrets** — `.env`, access tokens, credentials → `.gitignore`
- **Plaid Production** = real account data, free up to 100 connected items
- **BILT heads-up** — Wells Fargo partnership ended Feb 2026; Bilt is now on Cardless. Plaid connectivity has been reported as spotty across all budgeting apps. Test early.
- **Render cold start** — free tier spins down after inactivity; first daily trigger may take ~30s
- **Origin Financial** handles transaction tracking for Chris + Jeff. This project does NOT need to touch transactions anymore.

---

## Next Action

**Build is intentionally paused.** Per the Decision Note (2026-06-28), the next action is *measurement, not code*:

1. Spend **July 2026** using Origin's accounts screen at each month-end close.
2. Log the reconciliation in `project-artifacts/plaid-budget-sync/reconciliation_log.md` — how long it took, what was still manual/painful.
3. **End of July**, review the log and decide: if reconciliation shrank to "glance + 5 min," shelve Phase 2–4. If it's still painful, greenlight the build using the Auto-Fill Spec above (resolve open questions #2–6 first).

Phases 2–4 stay on hold until that decision.
