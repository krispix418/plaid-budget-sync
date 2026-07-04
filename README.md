# plaid-budget-sync

**A Plaid-powered planning layer for a Google Sheets financial hub.** 🏗️ *In active development, see status below.*

Most budgeting apps answer "what did I spend?" This project automates the question they don't: **is every card balance covered by money already set aside to pay it?** It pulls live balances and card liabilities from Plaid and writes them into the reconciliation section of a Google Sheets planning hub, replacing the monthly ritual of hand-copying numbers out of a dozen banking apps.

## Design philosophy: measure before you build

This project deliberately does less than it could. The original scope was a full transaction-sync budget tracker. After evaluating off-the-shelf tools, I offloaded transaction tracking to a dedicated app and re-scoped this to the one thing nothing else does: matching each card's balance to the funds earmarked to pay it.

Before building the final auto-fill phase, I'm measuring the remaining manual work for a month. If reconciliation shrinks to a 5-minute glance, the phase gets cut. Automation should earn its complexity.

## Architecture

```
Plaid API                Flask server (Render)              Google Sheets
Balance + Liabilities -> /balances endpoint             ->  Apps Script writes
(banks, cards)           Google OIDC JWT auth,              balances into the
                         email allowlist, rate limiting     reconciliation matrix
```

- **Flask backend.** Calls Plaid `/accounts/balance/get` and `/liabilities/get` and returns per-account JSON. Locked down with Google OIDC JWT verification, an email allowlist, and rate limiting, so the Sheet (and only the Sheet) can call it
- **Google Apps Script.** Fetches balances and fills the target cells, on demand or on a schedule
- **Plaid scope, minimized.** Only the Balance and Liabilities products, one access token per institution. Liabilities is what makes this useful for cards: statement balance, minimum payment, due date, APR

## Security and credential hygiene

- All secrets run through the **1Password CLI** (`op run --env-file=.env.template`). The env template holds `op://` references and is safe to commit, so real keys never touch the shell or the repo
- Access tokens and sync state are gitignored
- The server accepts only Google-signed JWTs from allowlisted accounts

## Current status

- ✅ Plaid client and sandbox integration (SDK, token exchange, cursor-based incremental sync)
- ✅ Transaction sync pipeline. Built, then archived after the re-scope (kept for reference)
- ✅ Flask server with the Google OIDC auth model
- ✅ Account connectivity research: institutions tiered by real-world Plaid reliability before anything depends on them
- 🔜 Swap `/transactions` for `/balances` plus Liabilities, and move to production Plaid credentials
- 🔜 Apps Script auto-fill, gated on the one-month manual-effort measurement

## Running

```bash
make sync   # = op run --env-file=.env.template -- python src/sync_transactions.py
```
