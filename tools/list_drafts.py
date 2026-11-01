"""List drafts created by this project and their live status on eBay.

  python3 tools/list_drafts.py
  python3 tools/list_drafts.py --show-policies   # your business policy IDs + inventory locations
"""
import argparse

import drafts_registry as reg
import ebay_client as ec


def show_policies():
    mp = ec.goals().get("marketplace_id", "EBAY_US")
    out = {}
    for kind, key in [("fulfillment_policy", "fulfillmentPolicies"),
                      ("payment_policy", "paymentPolicies"), ("return_policy", "returnPolicies")]:
        r = ec.rest("GET", f"/sell/account/v1/{kind}", params={"marketplace_id": mp})
        out[kind] = [{"id": x.get(f"{kind.split('_')[0]}PolicyId"), "name": x["name"]}
                     for x in r.json().get(key, [])]
    r = ec.rest("GET", "/sell/inventory/v1/location")
    out["locations"] = [{"key": x["merchantLocationKey"], "name": x.get("name")}
                        for x in r.json().get("locations", [])]
    ec.print_json(out)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--show-policies", action="store_true")
    p.add_argument("--offline", action="store_true", help="don't query eBay, just local specs")
    a = p.parse_args()
    if a.show_policies:
        show_policies()
    else:
        rows = []
        for path, spec in reg.all_specs():
            e = spec.get("ebay", {})
            row = {"sku": spec.get("sku"), "title": spec.get("title"), "price": spec.get("price"),
                   "offer_id": e.get("offer_id"), "status": e.get("status", "NOT_CREATED"),
                   "listing_id": e.get("listing_id"),
                   "needs_owner_input": spec.get("needs_owner_input", [])}
            if e.get("offer_id") and not a.offline:
                o = ec.rest("GET", f"/sell/inventory/v1/offer/{e['offer_id']}").json()
                row["status"] = o.get("status")
                row["listing_id"] = o.get("listing", {}).get("listingId")
                if row["status"] != e.get("status") or row["listing_id"] != e.get("listing_id"):
                    e["status"], e["listing_id"] = row["status"], row["listing_id"]
                    reg.save(path, spec)
            rows.append(row)
        ec.print_json(rows)
