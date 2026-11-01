"""Revise a live listing: price, quantity, title. DRY RUN unless --apply.

  python3 tools/update_listing.py <item_id> --price 64.99
  python3 tools/update_listing.py <item_id> --price 64.99 --title "New title" --apply
  python3 tools/update_listing.py <item_id> --description-file new.html --apply

Listings created by this project (Inventory API) are revised through the Inventory API;
everything else through the Trading API.
"""
import argparse
import pathlib

import drafts_registry as reg
import ebay_client as ec


def inventory_update(spec, a, cur):
    sku, offer_id = spec["sku"], spec["ebay"]["offer_id"]
    if a.price is not None or a.quantity is not None:
        o = {"offerId": offer_id}
        if a.price is not None:
            o["price"] = {"value": f"{a.price:.2f}", "currency": cur}
        if a.quantity is not None:
            o["availableQuantity"] = a.quantity
        req = {"sku": sku, "offers": [o]}
        if a.quantity is not None:
            req["shipToLocationAvailability"] = {"quantity": a.quantity}
        r = ec.rest("POST", "/sell/inventory/v1/bulk_update_price_quantity", json={"requests": [req]})
        ec.print_json(r.json())
    if a.title or a.description_file:
        item = ec.rest("GET", f"/sell/inventory/v1/inventory_item/{sku}").json()
        for k in ("sku", "locale", "groupIds", "inventoryItemGroupKeys"):
            item.pop(k, None)
        if a.title:
            item["product"]["title"] = a.title
        if a.description_file:
            item["product"]["description"] = pathlib.Path(a.description_file).read_text()
        ec.rest("PUT", f"/sell/inventory/v1/inventory_item/{sku}", json=item)
        if a.description_file:
            offer = ec.rest("GET", f"/sell/inventory/v1/offer/{offer_id}").json()
            offer["listingDescription"] = item["product"]["description"]
            for k in ("offerId", "status", "listing", "marketplaceId", "sku", "format"):
                offer.pop(k, None)
            ec.rest("PUT", f"/sell/inventory/v1/offer/{offer_id}", json=offer)
    # keep local spec in sync
    path = ec.ROOT / "data" / "drafts" / f"{sku}.json"
    if a.price is not None:
        spec["price"] = a.price
    if a.title:
        spec["title"] = a.title
    reg.save(path, spec)


def trading_update(a, cur):
    parts = [f"<ItemID>{ec.xml_escape(a.item_id)}</ItemID>"]
    if a.price is not None:
        parts.append(f'<StartPrice currencyID="{cur}">{a.price:.2f}</StartPrice>')
    if a.quantity is not None:
        parts.append(f"<Quantity>{a.quantity}</Quantity>")
    if a.title:
        parts.append(f"<Title>{ec.xml_escape(a.title)}</Title>")
    if a.description_file:
        html = pathlib.Path(a.description_file).read_text().replace("]]>", "]]&gt;")
        parts.append(f"<Description><![CDATA[{html}]]></Description>")
    root = ec.trading("ReviseFixedPriceItem", f"<Item>{''.join(parts)}</Item>")
    print(f"revised {root.findtext('e:ItemID', namespaces=ec.NS)}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("item_id")
    p.add_argument("--price", type=float)
    p.add_argument("--quantity", type=int)
    p.add_argument("--title")
    p.add_argument("--description-file")
    p.add_argument("--apply", action="store_true")
    a = p.parse_args()
    if not any([a.price is not None, a.quantity is not None, a.title, a.description_file]):
        ec.die("nothing to change; pass --price/--quantity/--title/--description-file")
    if a.title and len(a.title) > 80:
        ec.die(f"title is {len(a.title)} chars; max 80")
    cur = ec.goals().get("currency", "USD")
    spec = reg.find_by_listing_id(a.item_id)
    change = {k: v for k, v in vars(a).items() if k not in ("apply",) and v is not None}
    change["path"] = "inventory_api" if spec else "trading_api"
    if not a.apply:
        ec.print_json({"dry_run": True, "would_change": change})
    elif spec:
        inventory_update(spec, a, cur)
    else:
        trading_update(a, cur)
