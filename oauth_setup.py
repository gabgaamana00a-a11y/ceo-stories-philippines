"""
oauth_setup.py — One-time YouTube OAuth token setup.

Run this ONCE locally to generate token.json.
Then copy the contents into GitHub Secret: YOUTUBE_TOKEN_JSON

Usage:
    python oauth_setup.py

Requirements:
    - credentials.json in this folder (downloaded from Google Cloud Console)
    - pip install google-auth-oauthlib google-api-python-client
"""

import json
import os

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import google.oauth2.credentials

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
TOKEN_FILE = "token.json"
CREDS_FILE = "credentials.json"


def main():
    if not os.path.exists(CREDS_FILE):
        print(f"ERROR: {CREDS_FILE} not found.")
        print("Download it from: Google Cloud Console → APIs & Services → Credentials → OAuth 2.0 Client IDs → Download JSON")
        return

    creds = None

    # Load existing token if available
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE) as f:
                data = json.load(f)
        except (json.JSONDecodeError, ValueError):
            data = {}
        if data.get("token") or data.get("refresh_token"):
            with open(CREDS_FILE) as f:
                cred_data = json.load(f)
            installed = cred_data.get("installed", cred_data.get("web", {}))
            creds = google.oauth2.credentials.Credentials(
                token=data.get("token"),
                refresh_token=data.get("refresh_token"),
                token_uri=installed.get("token_uri"),
                client_id=installed.get("client_id"),
                client_secret=installed.get("client_secret"),
                scopes=SCOPES,
            )

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        # Save token
        with open(TOKEN_FILE, "w") as f:
            json.dump({
                "token":         creds.token,
                "refresh_token": creds.refresh_token,
                "token_uri":     creds.token_uri,
                "client_id":     creds.client_id,
                "client_secret": creds.client_secret,
            }, f, indent=2)
        print(f"\ntoken.json saved!")
        print("\nNow add these as GitHub Secrets:")
        print(f"  YOUTUBE_TOKEN_JSON        = contents of token.json")
        print(f"  YOUTUBE_CREDENTIALS_JSON  = contents of credentials.json")
    else:
        print("Token is still valid — no action needed.")


if __name__ == "__main__":
    main()
