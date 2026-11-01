---
description: Apply owner-approved recommendations from a report
argument-hint: "<report json path> <approved numbers, e.g. 1,3,5 or 'all price'>"
---
Act as the store-manager. Load the recommendations JSON: $ARGUMENTS

For ONLY the items I approved: show the exact command and the before → after, run it with
--apply / --confirm, and log the result to data/reports/actions-log.md. Skip and list anything
ambiguous. Report failures verbatim.
