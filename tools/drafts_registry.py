"""Helpers for the local draft registry in data/drafts/*.json."""
import json
import pathlib

import ebay_client as ec

DRAFTS = ec.ROOT / "data" / "drafts"


def load(sku: str) -> tuple[pathlib.Path, dict]:
    path = DRAFTS / f"{sku}.json"
    if not path.exists():
        ec.die(f"no draft spec at {path}")
    return path, json.loads(path.read_text())


def save(path: pathlib.Path, spec: dict):
    path.write_text(json.dumps(spec, indent=2))


def all_specs():
    for p in sorted(DRAFTS.glob("*.json")):
        yield p, json.loads(p.read_text())


def find_by_listing_id(item_id: str):
    """Return the spec of an Inventory-API listing created by this project, else None."""
    for _, spec in all_specs():
        if str(spec.get("ebay", {}).get("listing_id")) == str(item_id):
            return spec
    return None
