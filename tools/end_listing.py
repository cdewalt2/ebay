"""End (remove) a live listing. DRY RUN unless --confirm.

  python3 tools/end_listing.py <item_id>
  python3 tools/end_listing.py <item_id> --confirm [--reason NotAvailable]
"""
import argparse

import drafts_registry as reg
import ebay_client as ec

REASONS = ["NotAvailable", "Incorrect", "LostOrBroken", "OtherListingError", "SellToHighBidder"]

if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("item_id")
    p.add_argument("--reason", default="NotAvailable", choices=REASONS)
    p.add_argument("--confirm", action="store_true")
    a = p.parse_args()
    spec = reg.find_by_listing_id(a.item_id)
    if not a.confirm:
        ec.print_json({"dry_run": True, "would_end": a.item_id, "reason": a.reason,
                       "path": "inventory_api_withdraw" if spec else "trading_api"})
    elif spec:
        ec.rest("POST", f"/sell/inventory/v1/offer/{spec['ebay']['offer_id']}/withdraw")
        spec["ebay"]["status"] = "WITHDRAWN"
        reg.save(ec.ROOT / "data" / "drafts" / f"{spec['sku']}.json", spec)
        print(f"withdrew listing {a.item_id} (SKU {spec['sku']} kept; can be republished)")
    else:
        ec.trading("EndFixedPriceItem",
                   f"<ItemID>{ec.xml_escape(a.item_id)}</ItemID><EndingReason>{a.reason}</EndingReason>")
        print(f"ended listing {a.item_id}")
