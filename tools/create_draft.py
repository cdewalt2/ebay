"""Create an UNPUBLISHED eBay listing (draft) from a spec file written by the listing-drafter.

  python3 tools/create_draft.py data/drafts/<sku>.json

Steps: upload photos (Media API) -> create/replace inventory item -> create/update offer.
The offer stays UNPUBLISHED until you run publish_draft.py. Re-running is safe (idempotent per SKU).
"""
import argparse
import json
import mimetypes
import pathlib
import re

import drafts_registry as reg
import ebay_client as ec


def upload_image(path: pathlib.Path) -> str:
    mime = mimetypes.guess_type(path.name)[0] or "image/jpeg"
    with open(path, "rb") as f:
        r = ec.rest("POST", "/commerce/media/v1_beta/image/create_image_from_file", base=ec.APIM,
                    files={"image": (path.name, f, mime)})
    body = r.json() if r.content else {}
    if body.get("imageUrl"):
        return body["imageUrl"]
    loc = r.headers.get("Location", "")
    image_id = loc.rstrip("/").split("/")[-1]
    if not image_id:
        ec.die(f"image upload for {path} returned no URL or Location")
    r2 = ec.rest("GET", f"/commerce/media/v1_beta/image/{image_id}", base=ec.APIM)
    return r2.json()["imageUrl"]


def money(v, cur):
    return {"value": f"{float(v):.2f}", "currency": cur}


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("spec")
    a = p.parse_args()
    path = pathlib.Path(a.spec)
    spec = json.loads(path.read_text())
    g = ec.goals()
    cur = g.get("currency", "USD")
    sku = spec["sku"]
    if not re.fullmatch(r"[A-Za-z0-9\-_]{1,50}", sku):
        ec.die("sku must be <=50 chars of letters, digits, - or _")
    if len(spec["title"]) > 80:
        ec.die(f"title is {len(spec['title'])} chars; max 80")

    ebay = spec.setdefault("ebay", {})

    # 1) photos
    if not ebay.get("image_urls"):
        urls = []
        for img in spec["images"]:
            ip = (ec.ROOT / img) if not pathlib.Path(img).is_absolute() else pathlib.Path(img)
            if not ip.exists():
                ec.die(f"image not found: {ip}")
            urls.append(upload_image(ip))
            print(f"uploaded {ip.name}")
        ebay["image_urls"] = urls
        reg.save(path, spec)

    # 2) inventory item
    item = {
        "availability": {"shipToLocationAvailability": {"quantity": int(spec.get("quantity", 1))}},
        "condition": spec["condition"],
        "product": {
            "title": spec["title"],
            "description": spec["description_html"],
            "aspects": spec.get("aspects", {}),
            "imageUrls": ebay["image_urls"],
        },
    }
    if spec.get("condition_description"):
        item["conditionDescription"] = spec["condition_description"][:1000]
    ec.rest("PUT", f"/sell/inventory/v1/inventory_item/{sku}", json=item)
    print(f"inventory item {sku} saved")

    # 3) offer (unpublished)
    offer = {
        "sku": sku,
        "marketplaceId": g.get("marketplace_id", "EBAY_US"),
        "format": "FIXED_PRICE",
        "availableQuantity": int(spec.get("quantity", 1)),
        "categoryId": str(spec["category_id"]),
        "listingDescription": spec["description_html"],
        "listingDuration": "GTC",
        "merchantLocationKey": ec.env("EBAY_MERCHANT_LOCATION_KEY"),
        "pricingSummary": {"price": money(spec["price"], cur)},
        "listingPolicies": {
            "fulfillmentPolicyId": ec.env("EBAY_FULFILLMENT_POLICY_ID"),
            "paymentPolicyId": ec.env("EBAY_PAYMENT_POLICY_ID"),
            "returnPolicyId": ec.env("EBAY_RETURN_POLICY_ID"),
        },
    }
    bo = spec.get("best_offer") or {}
    if bo.get("enabled"):
        terms = {"bestOfferEnabled": True}
        if bo.get("auto_accept"):
            terms["autoAcceptPrice"] = money(bo["auto_accept"], cur)
        if bo.get("auto_decline"):
            terms["autoDeclinePrice"] = money(bo["auto_decline"], cur)
        offer["listingPolicies"]["bestOfferTerms"] = terms

    if ebay.get("offer_id"):
        ec.rest("PUT", f"/sell/inventory/v1/offer/{ebay['offer_id']}", json=offer)
        print(f"offer {ebay['offer_id']} updated")
    else:
        r = ec.rest("POST", "/sell/inventory/v1/offer", json=offer)
        ebay["offer_id"] = r.json()["offerId"]
        print(f"offer {ebay['offer_id']} created (UNPUBLISHED)")
    ebay["status"] = "UNPUBLISHED"
    ebay["env"] = ec.ENV
    reg.save(path, spec)
    projection = ec.fees_and_floor(spec["price"], spec.get("research", {}).get("cost"), g)
    ec.print_json({"sku": sku, "offer_id": ebay["offer_id"], "status": "UNPUBLISHED", **projection})


if __name__ == "__main__":
    main()
