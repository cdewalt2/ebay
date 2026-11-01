"""Shared eBay API client: OAuth tokens, REST + Trading API helpers, config loading."""
from __future__ import annotations

import base64
import json
import os
import pathlib
import sys
import time
import xml.etree.ElementTree as ET

import requests
import yaml
from dotenv import load_dotenv

ROOT = pathlib.Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

ENV = os.getenv("EBAY_ENV", "sandbox").lower()
PROD = ENV == "production"
API = "https://api.ebay.com" if PROD else "https://api.sandbox.ebay.com"
APIM = "https://apim.ebay.com" if PROD else "https://apim.sandbox.ebay.com"
AUTH_WEB = "https://auth.ebay.com" if PROD else "https://auth.sandbox.ebay.com"
TOKEN_URL = f"{API}/identity/v1/oauth2/token"
CACHE = ROOT / ".cache"

USER_SCOPES = [
    "https://api.ebay.com/oauth/api_scope",
    "https://api.ebay.com/oauth/api_scope/sell.inventory",
    "https://api.ebay.com/oauth/api_scope/sell.account",
    "https://api.ebay.com/oauth/api_scope/sell.analytics.readonly",
    "https://api.ebay.com/oauth/api_scope/sell.fulfillment.readonly",
]
APP_SCOPES = ["https://api.ebay.com/oauth/api_scope"]
TRADING_COMPAT_LEVEL = "1349"
NS = {"e": "urn:ebay:apis:eBLBaseComponents"}


def die(msg: str, code: int = 1):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def env(name: str, required: bool = True) -> str:
    val = os.getenv(name, "").strip()
    if required and not val:
        die(f"{name} is not set. Copy config/.env.example to .env and fill it in.")
    return val


def goals() -> dict:
    with open(ROOT / "config" / "goals.yaml") as f:
        return yaml.safe_load(f)


def _basic_auth() -> str:
    raw = f"{env('EBAY_CLIENT_ID')}:{env('EBAY_CLIENT_SECRET')}".encode()
    return "Basic " + base64.b64encode(raw).decode()


def _cached_token(kind: str, fetch) -> str:
    CACHE.mkdir(exist_ok=True)
    path = CACHE / f"{kind}_{ENV}.json"
    if path.exists():
        data = json.loads(path.read_text())
        if data.get("expires_at", 0) > time.time() + 120:
            return data["access_token"]
    resp = fetch()
    if resp.status_code != 200:
        die(f"token request failed ({resp.status_code}): {resp.text}")
    data = resp.json()
    data["expires_at"] = time.time() + int(data.get("expires_in", 7200))
    path.write_text(json.dumps(data))
    os.chmod(path, 0o600)
    return data["access_token"]


def user_token() -> str:
    """Access token acting as the seller (from the stored refresh token)."""
    refresh = env("EBAY_REFRESH_TOKEN")
    return _cached_token("user", lambda: requests.post(
        TOKEN_URL,
        headers={"Authorization": _basic_auth(), "Content-Type": "application/x-www-form-urlencoded"},
        data={"grant_type": "refresh_token", "refresh_token": refresh, "scope": " ".join(USER_SCOPES)},
        timeout=30))


def app_token() -> str:
    """Application token (client credentials) for public APIs: Browse, Taxonomy."""
    return _cached_token("app", lambda: requests.post(
        TOKEN_URL,
        headers={"Authorization": _basic_auth(), "Content-Type": "application/x-www-form-urlencoded"},
        data={"grant_type": "client_credentials", "scope": " ".join(APP_SCOPES)},
        timeout=30))


def rest(method: str, path: str, *, app: bool = False, base: str | None = None,
         ok=(200, 201, 204), **kw) -> requests.Response:
    headers = kw.pop("headers", {})
    headers.setdefault("Authorization", f"Bearer {app_token() if app else user_token()}")
    headers.setdefault("Accept", "application/json")
    if "json" in kw:
        headers.setdefault("Content-Type", "application/json")
        headers.setdefault("Content-Language", "en-US")
    url = (base or API) + path
    for attempt in range(3):
        resp = requests.request(method, url, headers=headers, timeout=60, **kw)
        if resp.status_code in (429, 500, 502, 503) and attempt < 2:
            time.sleep(2 ** (attempt + 1))
            continue
        break
    if resp.status_code not in ok:
        die(f"{method} {path} -> {resp.status_code}: {resp.text[:2000]}")
    return resp


def trading(call: str, inner_xml: str) -> ET.Element:
    """Call the Trading API (XML) with the OAuth user token. Returns the parsed root."""
    body = (f'<?xml version="1.0" encoding="utf-8"?>'
            f'<{call}Request xmlns="urn:ebay:apis:eBLBaseComponents">'
            f'<ErrorLanguage>en_US</ErrorLanguage><WarningLevel>High</WarningLevel>'
            f'{inner_xml}</{call}Request>')
    resp = requests.post(f"{API}/ws/api.dll", data=body.encode("utf-8"), timeout=60, headers={
        "X-EBAY-API-CALL-NAME": call,
        "X-EBAY-API-SITEID": "0",
        "X-EBAY-API-COMPATIBILITY-LEVEL": TRADING_COMPAT_LEVEL,
        "X-EBAY-API-IAF-TOKEN": user_token(),
        "Content-Type": "text/xml",
    })
    root = ET.fromstring(resp.content)
    ack = root.findtext("e:Ack", namespaces=NS)
    errors = [
        f"[{e.findtext('e:SeverityCode', namespaces=NS)}] {e.findtext('e:LongMessage', namespaces=NS)}"
        for e in root.findall("e:Errors", NS)
    ]
    if ack not in ("Success", "Warning"):
        die(f"{call} failed: " + " | ".join(errors))
    for w in errors:
        print(f"warning: {w}", file=sys.stderr)
    return root


def xml_escape(s: str) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


def fees_and_floor(price: float | None, cost: float | None, g: dict | None = None) -> dict:
    """Projected fees/profit at `price` and the minimum price that meets the owner's goals."""
    g = g or goals()
    pct = (g["final_value_fee_pct"] + g.get("promoted_listing_pct", 0)) / 100
    fixed = g["fixed_fee_per_order"] + g.get("avg_shipping_cost_absorbed", 0)
    out: dict = {}
    if price is not None:
        fees = price * pct + fixed
        out["projected_fees"] = round(fees, 2)
        if cost is not None:
            profit = price - fees - cost
            out["projected_profit"] = round(profit, 2)
            out["margin_pct"] = round(100 * profit / price, 1) if price else None
    if cost is not None:
        floor_profit = (cost + g["min_profit_per_item"] + fixed) / (1 - pct)
        floor_margin = (cost + fixed) / (1 - pct - g["min_margin_pct"] / 100)
        out["price_floor"] = round(max(floor_profit, floor_margin), 2)
    return out


def print_json(obj):
    print(json.dumps(obj, indent=2, default=str))
