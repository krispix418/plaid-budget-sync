"""
app.py

Flask server exposing Plaid transaction data to Google Apps Script.

Security layers:
  1. Google OIDC JWT verification — only requests signed by an authorized
     Google account are accepted (no shared secret to leak)
  2. Email allowlist — token must belong to ALLOWED_CALLER_EMAIL
  3. Rate limiting — 10 requests/minute as a backstop
  4. HTTPS enforced — handled by Render (all HTTP redirected to HTTPS)

Running locally:
    op run --env-file=.env.template -- .venv/bin/python src/app.py

Deploying to Render:
    Start command: gunicorn --chdir src app:app
"""

import json
import logging
import os

import requests
from flask import Flask, jsonify, request, abort
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from plaid_fetch import get_current_month_transactions

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

ALLOWED_CALLER_EMAIL = os.environ.get("ALLOWED_CALLER_EMAIL", "krispix418@gmail.com")

# Google's OIDC issuer — tokens from Apps Script use this
GOOGLE_ISSUER = "https://accounts.google.com"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = Flask(__name__)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["10 per minute"],
    storage_uri="memory://",
)


# ---------------------------------------------------------------------------
# Auth middleware
# ---------------------------------------------------------------------------

def verify_google_token() -> dict:
    """
    Verifies the Authorization: Bearer <token> header.
    Raises a 401 if missing, invalid, expired, wrong issuer, or wrong email.
    Returns the decoded token claims on success.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        logger.warning("Missing or malformed Authorization header")
        abort(401, description="Missing Authorization header")

    token = auth_header.split(" ", 1)[1]

    try:
        # Verify signature against Google's public keys and decode claims
        claims = id_token.verify_token(
            token,
            google_requests.Request(),
            audience=None,  # Apps Script identity tokens don't have a fixed audience
            clock_skew_in_seconds=30,
        )
    except Exception as e:
        logger.warning(f"Token verification failed: {e}")
        abort(401, description="Invalid or expired token")

    # Verify issuer
    if claims.get("iss") not in (GOOGLE_ISSUER, "accounts.google.com"):
        logger.warning(f"Unexpected token issuer: {claims.get('iss')}")
        abort(401, description="Invalid token issuer")

    # Verify caller is the authorized email
    caller_email = claims.get("email", "")
    if caller_email != ALLOWED_CALLER_EMAIL:
        logger.warning(f"Unauthorized caller: {caller_email}")
        abort(403, description="Caller not authorized")

    return claims


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/health")
def health():
    """Render health check — no auth required."""
    return jsonify({"status": "ok"})


@app.route("/transactions")
@limiter.limit("10 per minute")
def transactions():
    """
    Returns current month transactions as JSON.
    Requires a valid Google OIDC token from the authorized caller.
    """
    verify_google_token()

    access_token = os.environ.get("PLAID_ACCESS_TOKEN")
    if not access_token:
        logger.error("PLAID_ACCESS_TOKEN env var not set")
        abort(500, description="Server misconfiguration")

    try:
        txns = get_current_month_transactions(access_token)
        logger.info(f"Returned {len(txns)} transactions to authorized caller")
        return jsonify({"transactions": txns, "count": len(txns)})
    except Exception as e:
        logger.error(f"Error fetching transactions: {e}")
        abort(500, description="Failed to fetch transactions")


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------

@app.errorhandler(401)
def unauthorized(e):
    return jsonify({"error": "Unauthorized", "message": str(e.description)}), 401

@app.errorhandler(403)
def forbidden(e):
    return jsonify({"error": "Forbidden", "message": str(e.description)}), 403

@app.errorhandler(429)
def rate_limited(e):
    return jsonify({"error": "Rate limit exceeded", "message": "Too many requests"}), 429

@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Server error", "message": str(e.description)}), 500


# ---------------------------------------------------------------------------
# Local dev entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)
