"""Publish (make live) a draft created by create_draft.py. Requires --apply.

  python3 tools/publish_draft.py <sku>            # dry run: shows what would go live
  python3 tools/publish_draft.py <sku> --apply
"""
import argparse

import drafts_registry as reg
import ebay_client as ec

if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("sku")
    p.add_argument("--apply", action="store_true")
    a = p.parse_args()
    path, spec = reg.load(a.sku)
    offer_id = spec.get("ebay", {}).get("offer_id")
    if not offer_id:
        ec.die("draft has no offer_id; run create_draft.py first")
    summary = {"sku": a.sku, "title": spec["title"], "price": spec["price"], "offer_id": offer_id}
    if not a.apply:
        ec.print_json({"dry_run": True, "would_publish": summary})
    else:
        r = ec.rest("POST", f"/sell/inventory/v1/offer/{offer_id}/publish")
        listing_id = r.json()["listingId"]
        spec["ebay"].update(status="PUBLISHED", listing_id=listing_id)
        reg.save(path, spec)
        ec.print_json({"published": summary, "listing_id": listing_id})
