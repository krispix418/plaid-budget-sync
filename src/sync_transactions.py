"""
sync_transactions.py

Fetches transactions from Plaid and writes them to data/raw/ as CSV.

Usage:
    op run --env-file=.env.template -- python src/sync_transactions.py
    (or just: make sync)
"""

import csv
import json
import sys
from datetime import datetime
from pathlib import Path

import time

from plaid.exceptions import ApiException
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.products import Products
from plaid.model.sandbox_public_token_create_request import SandboxPublicTokenCreateRequest
from plaid.model.transactions_refresh_request import TransactionsRefreshRequest
from plaid.model.transactions_sync_request import TransactionsSyncRequest

from plaid_client import get_plaid_client

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
DATA_DIR = Path(__file__).parent.parent / "data"
RAW_DIR = DATA_DIR / "raw"
TOKEN_FILE = DATA_DIR / "access_token.json"
CURSOR_FILE = DATA_DIR / "cursors.json"

# Sandbox test institution — First Platypus Bank
SANDBOX_INSTITUTION_ID = "ins_109508"


# ---------------------------------------------------------------------------
# Token helpers
# ---------------------------------------------------------------------------

def get_or_create_access_token(client) -> str:
    """
    In sandbox: auto-creates a test access token if one doesn't exist yet.
    Persists the token locally so we reuse it across runs.
    """
    if TOKEN_FILE.exists():
        with open(TOKEN_FILE) as f:
            token = json.load(f).get("access_token")
        if token:
            print(f"🔑 Loaded existing access token from {TOKEN_FILE}")
            return token

    print("🏦 No access token found — creating sandbox test item...")

    pt_request = SandboxPublicTokenCreateRequest(
        institution_id=SANDBOX_INSTITUTION_ID,
        initial_products=[Products("transactions")],
    )
    pt_response = client.sandbox_public_token_create(pt_request)

    exchange_request = ItemPublicTokenExchangeRequest(
        public_token=pt_response["public_token"]
    )
    exchange_response = client.item_public_token_exchange(exchange_request)
    access_token = exchange_response["access_token"]

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(TOKEN_FILE, "w") as f:
        json.dump({"access_token": access_token}, f, indent=2)

    print(f"✅ Access token saved to {TOKEN_FILE}")

    # Trigger sandbox to generate test transaction data
    print("⏳ Triggering sandbox transaction refresh (takes a few seconds)...")
    client.transactions_refresh(TransactionsRefreshRequest(access_token=access_token))
    time.sleep(5)
    print("✅ Refresh complete")

    return access_token


# ---------------------------------------------------------------------------
# Cursor helpers (for transactions/sync pagination state)
# ---------------------------------------------------------------------------

def load_cursor(access_token: str) -> "str | None":
    if CURSOR_FILE.exists():
        with open(CURSOR_FILE) as f:
            return json.load(f).get(access_token)
    return None


def save_cursor(access_token: str, cursor: str) -> None:
    cursors = {}
    if CURSOR_FILE.exists():
        with open(CURSOR_FILE) as f:
            cursors = json.load(f)
    cursors[access_token] = cursor
    with open(CURSOR_FILE, "w") as f:
        json.dump(cursors, f, indent=2)


# ---------------------------------------------------------------------------
# Sync
# ---------------------------------------------------------------------------

def sync_transactions(client, access_token: str):
    """
    Calls /transactions/sync, paginating until has_more is False.
    Returns (added, modified, removed) lists.
    """
    cursor = load_cursor(access_token)
    added, modified, removed = [], [], []
    has_more = True

    while has_more:
        kwargs = {"access_token": access_token}
        if cursor:
            kwargs["cursor"] = cursor

        response = client.transactions_sync(TransactionsSyncRequest(**kwargs))
        added.extend(response["added"])
        modified.extend(response["modified"])
        removed.extend(response["removed"])
        has_more = response["has_more"]
        cursor = response["next_cursor"]

    save_cursor(access_token, cursor)
    return added, modified, removed


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

FIELDS = [
    "transaction_id",
    "account_id",
    "date",
    "name",
    "merchant_name",
    "amount",
    "iso_currency_code",
    "category",
    "pending",
    "payment_channel",
]


def txn_to_row(txn) -> dict:
    category = txn.get("category") or []
    return {
        "transaction_id": txn["transaction_id"],
        "account_id": txn["account_id"],
        "date": txn["date"],
        "name": txn["name"],
        "merchant_name": txn.get("merchant_name") or "",
        "amount": txn["amount"],
        "iso_currency_code": txn.get("iso_currency_code") or "",
        "category": " > ".join(category),
        "pending": txn["pending"],
        "payment_channel": txn.get("payment_channel") or "",
    }


def write_csv(transactions: list, filepath: Path) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for txn in transactions:
            writer.writerow(txn_to_row(txn))
    print(f"  📄 {len(transactions)} rows → {filepath}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("🔌 Connecting to Plaid...")
    try:
        client = get_plaid_client()
    except KeyError as e:
        print(f"❌ Missing environment variable: {e}")
        print("   Make sure to run via: op run --env-file=.env.template -- python src/sync_transactions.py")
        sys.exit(1)

    access_token = get_or_create_access_token(client)

    print("🔄 Syncing transactions...")
    try:
        added, modified, removed = sync_transactions(client, access_token)
    except ApiException as e:
        print(f"❌ Plaid API error: {e}")
        sys.exit(1)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if added:
        write_csv(added, RAW_DIR / f"transactions_added_{timestamp}.csv")
    if modified:
        write_csv(modified, RAW_DIR / f"transactions_modified_{timestamp}.csv")

    print(
        f"\n✅ Sync complete — "
        f"{len(added)} added, {len(modified)} modified, {len(removed)} removed"
    )


if __name__ == "__main__":
    main()
