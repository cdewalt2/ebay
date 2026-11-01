"""All ACTIVE listings in the store (Trading API GetMyeBaySelling).

  python3 tools/get_listings.py [--out data/listings.json]
"""
import argparse
import datetime as dt
import json

import ebay_client as ec

NS = ec.NS


def t(el, path):
    return el.findtext(path, namespaces=NS)


def fetch_active() -> list[dict]:
    items, page, pages = [], 1, 1
    now = dt.datetime.now(dt.timezone.utc)
    while page <= pages:
        root = ec.trading("GetMyeBaySelling", (
            "<ActiveList><Include>true</Include><IncludeWatchCount>true</IncludeWatchCount>"
            f"<Pagination><EntriesPerPage>200</EntriesPerPage><PageNumber>{page}</PageNumber></Pagination>"
            "</ActiveList><DetailLevel>ReturnAll</DetailLevel>"))
        al = root.find("e:ActiveList", NS)
        if al is None:
            break
        pages = int(t(al, "e:PaginationResult/e:TotalNumberOfPages") or 1)
        for it in al.findall("e:ItemArray/e:Item", NS):
            start = t(it, "e:ListingDetails/e:StartTime")
            days = None
            if start:
                days = (now - dt.datetime.fromisoformat(start.replace("Z", "+00:00"))).days
            price = t(it, "e:SellingStatus/e:CurrentPrice") or t(it, "e:BuyItNowPrice")
            items.append({
                "item_id": t(it, "e:ItemID"),
                "sku": t(it, "e:SKU"),
                "title": t(it, "e:Title"),
                "price": float(price) if price else None,
                "quantity_available": int(t(it, "e:QuantityAvailable") or 0),
                "quantity_sold": int(t(it, "e:SellingStatus/e:QuantitySold") or 0),
                "watchers": int(t(it, "e:WatchCount") or 0),
                "listing_type": t(it, "e:ListingType"),
                "start_time": start,
                "days_listed": days,
                "url": t(it, "e:ListingDetails/e:ViewItemURL"),
            })
        page += 1
    return items


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out")
    a = p.parse_args()
    rows = fetch_active()
    if a.out:
        (ec.ROOT / a.out).write_text(json.dumps(rows, indent=2))
        print(f"wrote {len(rows)} listings to {a.out}")
    else:
        ec.print_json(rows)
