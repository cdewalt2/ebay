---
description: Have the listing-monitor review active listings and recommend changes
argument-hint: "[optional scope: item IDs, keyword, or 'stale']"
---
Act as the store-manager (see .claude/agents/store-manager.md).

Launch the **listing-monitor** subagent with scope: ${ARGUMENTS:-all active listings}.
Quality-check its recommendations against config/goals.yaml, then present them as a numbered
decision list (Price changes / Detail updates / End listings). Do NOT apply anything until I approve.
