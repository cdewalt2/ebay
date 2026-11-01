# eBay Store Agents

This project runs an eBay store with three agents:

| Agent | File | Job |
|---|---|---|
| **store-manager** | `.claude/agents/store-manager.md` | Orchestrates the other two, enforces goals, reports results, gets approval before anything goes live |
| **listing-drafter** | `.claude/agents/listing-drafter.md` | Turns photos in `inbox/` into **unpublished draft** listings on eBay |
| **listing-monitor** | `.claude/agents/listing-monitor.md` | Analyzes active listings and recommends price/detail changes or ending listings |

## The main session is the manager
Subagents cannot launch other subagents, so the **main Claude Code session acts as the
store-manager**. At the start of any store-related task, read
`.claude/agents/store-manager.md` and follow its playbook. To run the whole session as the
manager, start Claude Code with `claude --agent store-manager`.

## Hard rules (apply to every agent)
1. **Nothing goes live without the owner's explicit approval.** Drafts stay unpublished.
   Price changes, revisions, publishing and ending listings only happen after the owner
   says yes to the specific item and change.
2. Write tools default to dry-run. Only pass `--apply` / `--confirm` after approval.
3. Goals, margins and fees come from `config/goals.yaml`. Item costs come from
   `data/cost_basis.csv`. Never invent a cost. If it's missing, say so.
4. Never read, print or commit `.env` (it holds eBay credentials).
5. Every run writes its output to `data/` so there is an audit trail.

## Tools (run from the project root with `python3 tools/<script> --help`)
Read-only:
- `taxonomy.py suggest "<query>"` / `taxonomy.py aspects <category_id>`: category and item specifics
- `search_comps.py "<query>"`: active comparable listings and price stats (Browse API)
- `get_listings.py`: all active listings (Trading API)
- `get_traffic.py --days 30`: impressions, views, CTR and conversion per listing (Analytics API)
- `store_snapshot.py`: listings + traffic + cost basis merged into `data/snapshots/`
- `list_drafts.py`: drafts this project created and their status

Write (approval required):
- `create_draft.py <spec.json>`: uploads photos, creates inventory item + **unpublished** offer
- `publish_draft.py <sku> --apply`: makes a draft live
- `update_listing.py <item_id> [--price X] [--title ...] [--quantity N] --apply`
- `end_listing.py <item_id> --confirm`

## Slash commands
- `/draft`: draft listings for every photo set in `inbox/`
- `/review-listings`: run the monitor and get recommendations
- `/store-report`: full manager cycle: drafts + review + summary report
- `/apply-recommendations <report file>`: walk through approved changes one by one
