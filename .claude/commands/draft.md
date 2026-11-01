---
description: Draft eBay listings from photos in inbox/ (one folder per item)
argument-hint: "[optional folder or files]"
---
Act as the store-manager (see .claude/agents/store-manager.md).

Target: $ARGUMENTS (if empty, every subfolder of `inbox/` except `_drafted`; loose images directly
in `inbox/` are treated as one item each).

Launch the **listing-drafter** subagent for the target items. Run independent items in parallel.
Then quality-check the drafts per the manager playbook and give me a summary table plus any
questions I need to answer. Do NOT publish anything.
