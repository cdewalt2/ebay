"""Per-listing traffic (Analytics API traffic report): impressions, views, CTR, conversion, sales.

  python3 tools/get_traffic.py --days 30 [--listing-ids 123,456]
"""
import argparse
import datetime as dt

import ebay_client as ec

METRICS = ["LISTING_IMPRESSION_TOTAL", "LISTING_VIEWS_TOTAL", "CLICK_THROUGH_RATE",
           "SALES_CONVERSION_RATE", "TRANSACTION"]
NAMES = {"LISTING_IMPRESSION_TOTAL": "impressions", "LISTING_VIEWS_TOTAL": "views",
         "CLICK_THROUGH_RATE": "ctr", "SALES_CONVERSION_RATE": "conversion",
         "TRANSACTION": "transactions"}


def fetch(days: int = 30, listing_ids: list[str] | None = None) -> dict[str, dict]:
    days = max(1, min(days, 90))
    end = dt.date.today() - dt.timedelta(days=1)   # data lags ~1 day
    start = end - dt.timedelta(days=days - 1)
    mp = ec.goals().get("marketplace_id", "EBAY_US")
    out: dict[str, dict] = {}
    batches = [listing_ids[i:i + 200] for i in range(0, len(listing_ids), 200)] if listing_ids else [None]
    for batch in batches:
        f = f"marketplace_ids:{{{mp}}},date_range:[{start:%Y%m%d}..{end:%Y%m%d}]"
        if batch:
            f += ",listing_ids:{" + "|".join(batch) + "}"
        r = ec.rest("GET", "/sell/analytics/v1/traffic_report", params={
            "dimension": "LISTING", "metric": ",".join(METRICS), "filter": f})
        data = r.json()
        keys = [m["key"] for m in data.get("header", {}).get("metrics", [])]
        for rec in data.get("records", []):
            lid = rec["dimensionValues"][0]["value"]
            row = {"period_days": days}
            for k, mv in zip(keys, rec.get("metricValues", [])):
                row[NAMES.get(k, k)] = mv.get("value")
            out[lid] = row
    return out


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--days", type=int, default=30)
    p.add_argument("--listing-ids")
    a = p.parse_args()
    ec.print_json(fetch(a.days, a.listing_ids.split(",") if a.listing_ids else None))
