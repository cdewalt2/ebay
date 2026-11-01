"""Find comparable ACTIVE listings and price stats via the Browse API.

  python3 tools/search_comps.py "nike air force 1 white size 10" --condition USED --limit 50
Note: these are asking prices of live listings, not sold prices.
"""
import argparse
import statistics

import ebay_client as ec

COND_IDS = {"NEW": "1000", "USED": "3000"}


def pct(sorted_vals, p):
    if not sorted_vals:
        return None
    k = (len(sorted_vals) - 1) * p
    lo, hi = int(k), min(int(k) + 1, len(sorted_vals) - 1)
    return round(sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (k - lo), 2)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("query")
    p.add_argument("--condition", choices=["NEW", "USED"])
    p.add_argument("--category-id")
    p.add_argument("--limit", type=int, default=50)
    p.add_argument("--price", type=float, help="your price, to report its percentile")
    p.add_argument("--exclude-item-id", help="your own listing, to leave out of comps")
    a = p.parse_args()
    g = ec.goals()

    filters = ["buyingOptions:{FIXED_PRICE}", f"priceCurrency:{g.get('currency', 'USD')}"]
    if a.condition:
        filters.append(f"conditionIds:{{{COND_IDS[a.condition]}}}")
    params = {"q": a.query, "limit": min(a.limit, 200), "filter": ",".join(filters)}
    if a.category_id:
        params["category_ids"] = a.category_id
    r = ec.rest("GET", "/buy/browse/v1/item_summary/search", app=True, params=params,
                headers={"X-EBAY-C-MARKETPLACE-ID": g.get("marketplace_id", "EBAY_US")})
    items = []
    for it in r.json().get("itemSummaries", []):
        if a.exclude_item_id and a.exclude_item_id in it.get("itemId", ""):
            continue
        price = float(it["price"]["value"])
        ship = it.get("shippingOptions", [{}])[0].get("shippingCost", {}).get("value")
        items.append({"title": it["title"], "price": price,
                      "shipping": float(ship) if ship is not None else None,
                      "condition": it.get("condition"), "url": it.get("itemWebUrl")})
    prices = sorted(i["price"] for i in items)
    stats = {"count": len(prices)}
    if prices:
        stats.update(min=prices[0], p25=pct(prices, .25), median=round(statistics.median(prices), 2),
                     p75=pct(prices, .75), max=prices[-1])
        if a.price is not None:
            stats["your_price_percentile"] = round(100 * sum(x < a.price for x in prices) / len(prices))
    ec.print_json({"query": a.query, "stats": stats, "comps": items[:25]})
