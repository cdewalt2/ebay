# eBay Store Agents (Claude Code)

Three Claude Code agents that run your eBay store:

```
                 ┌──────────────────────┐
     you  ◄────► │    store-manager     │  delegates, checks work against your goals,
                 │ (main Claude session)│  reports, applies ONLY what you approve
                 └─────────┬────────────┘
             ┌─────────────┴──────────────┐
   ┌─────────▼─────────┐        ┌─────────▼─────────┐
   │  listing-drafter  │        │  listing-monitor  │
   │ photos → eBay     │        │ traffic + comps → │
   │ UNPUBLISHED drafts│        │ price/detail/END  │
   └───────────────────┘        │ recommendations   │
                                └───────────────────┘
```

## 1. Setup (one time, ~20 min)

1. **Install**: `pip install -r requirements.txt`
2. **eBay developer keys**: sign up at https://developer.ebay.com → *Application Keys*.
   Create a **Sandbox** keyset first (for testing), then **Production** later.
   Under *User Tokens* → *Get a Token from eBay via Your Application*, add a redirect URL;
   copy its **RuName**.
3. **Config**: `cp config/.env.example .env` and fill in `EBAY_CLIENT_ID`, `EBAY_CLIENT_SECRET`,
   `EBAY_RUNAME`, `EBAY_ENV`.
4. **Authorize your seller account**: `python3 tools/auth_setup.py` (opens a consent URL,
   stores a refresh token).
5. **Business policies**: your account must be opted into business policies (Seller Hub →
   Account → Business policies). Then `python3 tools/list_drafts.py --show-policies` and put
   the shipping/payment/return policy IDs in `.env`.
6. **Inventory location**: `python3 tools/auth_setup.py --create-location --postal-code <zip>`
7. **Your goals**: edit `config/goals.yaml` (min profit, margin, max days listed, fees).
   Add what you paid for items to `data/cost_basis.csv` so profit math is real.

## 2. Daily use

```bash
cd ebay-store-agents
claude                       # or: claude --agent store-manager
```

| You type | What happens |
|---|---|
| Drop photos in `inbox/<item>/` (+ optional `notes.txt`: cost, flaws, size), then `/draft` | Drafter identifies each item, picks category & specifics, prices from comps, creates **unpublished** drafts |
| `/review-listings` | Monitor snapshots all listings + 30-day traffic, compares to comps & your goals, writes recommendations |
| `/store-report` | Both of the above in parallel, then a manager summary with numbered decisions |
| "approve 1, 3, 5" or `/apply-recommendations data/reports/recommendations-<date>.json 1,3,5` | Manager applies only those, logs to `data/reports/actions-log.md` |
| "publish 20261101-nike-af1" | `publish_draft.py --apply` (you'll get a permission prompt) |

## Safety model
- Drafts are created as **unpublished offers**. Nothing goes live without you.
- `publish_draft`, `update_listing`, `end_listing` are dry-run by default and are set to
  **ask** for permission in `.claude/settings.json`.
- The monitor agent has no access to write tools in its instructions. It only recommends.
- `.env` is gitignored and blocked from Claude's Read tool.

## Important notes / limitations
- **Where drafts show up**: drafts are created with eBay's Inventory API as *unpublished
  offers*. eBay generally does **not** show API-created unpublished offers in Seller Hub's
  "Drafts" tab. Review them with `/draft` output, `python3 tools/list_drafts.py`, or the
  JSON in `data/drafts/`, and publish with `publish_draft.py`. (eBay's Listing API
  `createItemDraft`, which creates Seller Hub-visible drafts, is a limited-release API that
  requires eBay approval. If you get access, `create_draft.py` is the one file to swap.)
- **Inventory API vs. Seller Hub listings**: items published by this project are
  "inventory-based" and must be revised through the API (the tools handle this
  automatically). Listings you made in Seller Hub are revised via the Trading API.
- **Comps are active asking prices** (Browse API). Sold-price data (Marketplace Insights
  API) is restricted by eBay. The agents can supplement with web research.
- **Fees** in `goals.yaml` are approximations. Check them against your category and
  store subscription.
- Start in **sandbox** (`EBAY_ENV=sandbox`). Switch to `production` once you're happy.
