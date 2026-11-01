"""One-time: authorize this app on your eBay seller account and store the refresh token in .env.

Usage:
  python3 tools/auth_setup.py                 # get a refresh token
  python3 tools/auth_setup.py --create-location --postal-code 90210 --country US
"""
import argparse
import re
import urllib.parse

import requests

import ebay_client as ec


def set_env_var(name: str, value: str):
    path = ec.ROOT / ".env"
    text = path.read_text() if path.exists() else ""
    line = f"{name}={value}"
    if re.search(rf"^{name}=.*$", text, flags=re.M):
        text = re.sub(rf"^{name}=.*$", line, text, flags=re.M)
    else:
        text += ("\n" if text and not text.endswith("\n") else "") + line + "\n"
    path.write_text(text)


def get_refresh_token():
    params = {
        "client_id": ec.env("EBAY_CLIENT_ID"),
        "redirect_uri": ec.env("EBAY_RUNAME"),
        "response_type": "code",
        "scope": " ".join(ec.USER_SCOPES),
    }
    url = f"{ec.AUTH_WEB}/oauth2/authorize?" + urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
    print("\n1) Open this URL, sign in with your SELLER account and click 'Agree':\n")
    print(url)
    print("\n2) After you're redirected, copy the FULL URL from the address bar and paste it here.")
    redirected = input("\nRedirected URL: ").strip()
    qs = urllib.parse.parse_qs(urllib.parse.urlparse(redirected).query)
    code = qs.get("code", [redirected])[0]
    resp = requests.post(ec.TOKEN_URL, timeout=30, headers={
        "Authorization": ec._basic_auth(), "Content-Type": "application/x-www-form-urlencoded"},
        data={"grant_type": "authorization_code", "code": code, "redirect_uri": ec.env("EBAY_RUNAME")})
    if resp.status_code != 200:
        ec.die(f"code exchange failed: {resp.text}")
    set_env_var("EBAY_REFRESH_TOKEN", resp.json()["refresh_token"])
    print("Saved EBAY_REFRESH_TOKEN to .env (valid ~18 months).")


def create_location(postal: str, country: str, key: str):
    ec.rest("POST", f"/sell/inventory/v1/location/{key}", json={
        "location": {"address": {"postalCode": postal, "country": country}},
        "locationTypes": ["WAREHOUSE"], "name": "Primary", "merchantLocationStatus": "ENABLED"})
    set_env_var("EBAY_MERCHANT_LOCATION_KEY", key)
    print(f"Created inventory location '{key}' and saved it to .env")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--create-location", action="store_true")
    p.add_argument("--postal-code")
    p.add_argument("--country", default="US")
    p.add_argument("--location-key", default="primary")
    a = p.parse_args()
    if a.create_location:
        if not a.postal_code:
            ec.die("--postal-code is required with --create-location")
        create_location(a.postal_code, a.country, a.location_key)
    else:
        get_refresh_token()
