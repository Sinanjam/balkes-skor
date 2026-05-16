# TFF Factory v3.4 Push Safe Chain

v3.4 focuses on three failures seen in the v3.3 chain artifact:

1. `workflow_dispatch` was unreliable/hidden, so v3.4 no longer depends on manual dispatch for the chain. It is triggered by committing `.github/tff-chain-v34-trigger.json`.
2. Failed/timeout groups must not push an empty `data/manifest.json` to live `main/data`.
3. Season summaries must not mix match-derived stats and official league-table stats. v3.4 writes match stats and official `leagueTable` separately, and infers point deductions when the official table is lower than match-result points.

## Start

```fish
fish start_v34_chain.fish
```

This creates `.github/tff-chain-v34-trigger.json` with:

- start: `2025-2026`
- end year: `1990`
- group size: `4`
- wait: `5` minutes
- standings: enabled
- clean all before first group: enabled

The workflow processes one group and then commits the next trigger file to continue the chain.

## Data safety

The workflow checks:

```text
availableSeasons > 0
totalAppMatches > 0
```

If either is zero, the workflow refuses to push `data/` to `main` and only preserves diagnostics as artifacts.

## Summary reconciliation

`reconcile_data_v34.py` writes:

- `summary` from actual published match JSON files
- `summary.leagueMatchStats` from league-only matches
- `summary.leagueTable` from official TFF standings, when present
- inferred `pointsDeducted` when official table points are lower than match-result points

This prevents mixed summaries like match losses from one source and goals/points from another.
