"""Category suggestions and item specifics (aspects) from the eBay Taxonomy API.

  python3 tools/taxonomy.py suggest "nike air force 1 white mens"
  python3 tools/taxonomy.py aspects 15709
"""
import argparse

import ebay_client as ec


def tree_id(marketplace: str) -> str:
    r = ec.rest("GET", "/commerce/taxonomy/v1/get_default_category_tree_id", app=True,
                params={"marketplace_id": marketplace})
    return r.json()["categoryTreeId"]


def suggest(q: str, tid: str):
    r = ec.rest("GET", f"/commerce/taxonomy/v1/category_tree/{tid}/get_category_suggestions",
                app=True, params={"q": q})
    out = []
    for s in r.json().get("categorySuggestions", [])[:10]:
        path = " > ".join(a["categoryName"] for a in reversed(s.get("categoryTreeNodeAncestors", [])))
        out.append({"category_id": s["category"]["categoryId"],
                    "name": s["category"]["categoryName"], "path": path})
    ec.print_json(out)


def aspects(cat: str, tid: str):
    r = ec.rest("GET", f"/commerce/taxonomy/v1/category_tree/{tid}/get_item_aspects_for_category",
                app=True, params={"category_id": cat})
    out = []
    for a in r.json().get("aspects", []):
        c = a.get("aspectConstraint", {})
        vals = [v["localizedValue"] for v in a.get("aspectValues", [])[:25]]
        out.append({
            "name": a["localizedAspectName"],
            "required": c.get("aspectRequired", False),
            "usage": c.get("aspectUsage"),
            "mode": c.get("aspectMode"),            # FREE_TEXT or SELECTION_ONLY
            "multi": c.get("itemToAspectCardinality") == "MULTI",
            "sample_values": vals,
        })
    out.sort(key=lambda x: (not x["required"], x["usage"] != "RECOMMENDED"))
    ec.print_json(out)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("suggest"); s.add_argument("query")
    a = sub.add_parser("aspects"); a.add_argument("category_id")
    args = p.parse_args()
    tid = tree_id(ec.goals().get("marketplace_id", "EBAY_US"))
    suggest(args.query, tid) if args.cmd == "suggest" else aspects(args.category_id, tid)
