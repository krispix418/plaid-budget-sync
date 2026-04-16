import os
import plaid
from plaid.api import plaid_api


ENV_MAP = {
    "sandbox": plaid.Environment.Sandbox,
    "production": plaid.Environment.Production,
}


def get_plaid_client() -> plaid_api.PlaidApi:
    """Initialize and return a Plaid API client from environment variables."""
    env = os.environ.get("PLAID_ENV", "sandbox").lower()

    if env not in ENV_MAP:
        raise ValueError(f"Unknown PLAID_ENV: '{env}'. Must be sandbox or production.")

    configuration = plaid.Configuration(
        host=ENV_MAP[env],
        api_key={
            "clientId": os.environ["PLAID_CLIENT_ID"],
            "secret": os.environ["PLAID_SECRET"],
        },
    )

    api_client = plaid.ApiClient(configuration)
    return plaid_api.PlaidApi(api_client)
