"""
plaid_fetch.py

Stateless transaction fetcher using /transactions/get with a date range.
Used by the Flask server (no cursor state, no file I/O — safe for Render).
"""

from datetime import date, datetime
from plaid.model.transactions_get_request import TransactionsGetRequest
from plaid.model.transactions_get_request_options import TransactionsGetRequestOptions

from plaid_client import get_plaid_client


def get_current_month_transactions(access_token: str) -> list:
    """
    Fetches all transactions for the current calendar month.
    Paginates automatically if there are more than 500 transactions.
    Returns a list of dicts ready to serialize as JSON.
    """
    client = get_plaid_client()

    today = date.today()
    start_date = today.replace(day=1)
    end_date = today

    all_transactions = []
    offset = 0
    total = None

    while total is None or offset < total:
        options = TransactionsGetRequestOptions(offset=offset, count=500)
        request = TransactionsGetRequest(
            access_token=access_token,
            start_date=start_date,
            end_date=end_date,
            options=options,
        )
        response = client.transactions_get(request)

        transactions = response["transactions"]
        all_transactions.extend(transactions)

        total = response["total_transactions"]
        offset += len(transactions)

        if not transactions:
            break

    return [_serialize(t) for t in all_transactions]


def _serialize(txn) -> dict:
    """Convert a Plaid transaction object to a JSON-safe dict."""
    category = txn.get("category") or []
    date_val = txn.get("date")

    return {
        "transaction_id": txn["transaction_id"],
        "account_id": txn["account_id"],
        "date": date_val.isoformat() if isinstance(date_val, (date, datetime)) else str(date_val),
        "name": txn["name"],
        "merchant_name": txn.get("merchant_name") or "",
        "amount": float(txn["amount"]),
        "iso_currency_code": txn.get("iso_currency_code") or "",
        "category": " > ".join(category),
        "pending": bool(txn["pending"]),
        "payment_channel": txn.get("payment_channel") or "",
    }
