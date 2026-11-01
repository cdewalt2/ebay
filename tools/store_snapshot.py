"""Snapshot of the whole store for the listing-monitor: listings + traffic + cost basis + goal math.

  python3 tools/store_snapshot.py --days 30
Writes data/snapshots/snapshot-YYYY-MM-DD.json and prints a short summary.
"""
import argparse
import csv
import datetime as dt
import json

import ebay_client as ec
import get_listings
import get_traffic


def load_costs() -> dict[str, float]:
    path = ec.ROOT / "data" / "cost_basis.csv"
    costs = {}
    if path.exists():
        for row in csv.DictReader(path.open()):
            try:
                costs[row["sku_or_item_id"].strip()] = float(row["cost"])
            except (KeyError, ValueError):
                continue
    return costs


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--days", type=int, default=30)
    a = p.parse_args()
    g = ec.goals()
    listings = get_listings.fetch_active()
    traffic = get_traffic.fetch(a.days) if listings else {}
    costs = load_costs()

    for l in listings:
        l["traffic"] = traffic.get(l["item_id"], {})
        cost = costs.get(l["item_id"]) or (costs.get(l["sku"]) if l["sku"] else None)
        l["cost"] = cost
        l.update(ec.fees_and_floor(l["price"], cost, g))
        flags = []
        if cost is None:
            flags.append("cost_unknown")
        if l.get("price_floor") and l["price"] is not None and l["price"] < l["price_floor"]:
            flags.append("below_profit_floor")
        if l["days_listed"] is not None and l["days_listed"] > g["max_days_listed"]:
            flags.append("over_max_days")
        if l["days_listed"] is not None and l["days_listed"] > g["target_days_to_sell"]:
            flags.append("over_target_days")
        imp = float(l["traffic"].get("impressions") or 0)
        views = float(l["traffic"].get("views") or 0)
        if l["traffic"] and imp < 50:
            flags.append("low_impressions")
        if imp >= 200 and views / imp < 0.01:
            flags.append("low_ctr")
        if views >= 30 and int(l["traffic"].get("transactions") or 0) == 0:
            flags.append("views_no_sales")
        l["flags"] = flags

    snap = {"taken_at": dt.datetime.now().isoformat(timespec="seconds"), "env": ec.ENV,
            "traffic_period_days": a.days, "goals": g, "listings": listings}
    out = ec.ROOT / "data" / "snapshots" / f"snapshot-{dt.date.today()}.json"
    out.write_text(json.dumps(snap, indent=2))
    total = sum((l["price"] or 0) * l["quantity_available"] for l in listings)
    flagged = {}
    for l in listings:
        for f in l["flags"]:
            flagged[f] = flagged.get(f, 0) + 1
    ec.print_json({"snapshot": str(out.relative_to(ec.ROOT)), "active_listings": len(listings),
                   "total_listed_value": round(total, 2), "flag_counts": flagged})
