# Plaid Budget Sync

## Overview
Automated household transaction sync via Plaid API with a dbt transformation layer and Google Sheets output

## Tech Stack
- **Language:** Python 3.9+
- **Plaid SDK:** plaid-python >= 20.0.0
- **Secrets:** 1Password CLI (`op run --env-file=.env.template`)
- **Data output:** CSV → `data/raw/` (dbt source layer)
- **Transformation:** dbt (TBD)
- **Output:** Google Sheets (TBD)

## Project Structure
```
plaid-budget-sync/
├── .env.template          # op:// references — safe to commit, never put real keys here
├── Makefile               # `make sync` to run the full fetch
├── requirements.txt
├── data/
│   ├── access_token.json  # gitignored — sandbox access token
│   ├── cursors.json       # gitignored — sync cursor state
│   └── raw/               # gitignored — CSV outputs from Plaid
└── src/
    ├── plaid_client.py    # Plaid SDK client init
    └── sync_transactions.py  # Main sync script
```

## Running the Sync
```bash
make sync
# or explicitly:
op run --env-file=.env.template -- .venv/bin/python src/sync_transactions.py
```

## Development Notes
- Always run via `op run` — never set `PLAID_CLIENT_ID` / `PLAID_SECRET` manually in shell
- Cursor state in `data/cursors.json` makes runs incremental — delete it to do a full re-sync
- Delete `data/access_token.json` to force a new sandbox item (also wipes cursor state)
- plaid-python SDK dropped `Development` env — only `sandbox` and `production` are valid
- Python 3.9 doesn't support `X | None` type union syntax — use `Optional[X]` or `"X | None"` string form
