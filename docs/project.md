# Project Design Notes

Notes on how *The Price of Prestige* is organized, and why it is organized that
way. Intended for future maintainers and reviewers.

## Goals

1. **Reproducible** — one command (`make pipeline`) takes a clean machine from
   zero to a full results set and figures.
2. **Auditable** — every number in the article traces to
   `outputs/results.json`, which traces to a documented transformation of
   public data.
3. **Publishable** — the deliverable is a polished feature article
   (`index.qmd`), not just a notebook.

## Pipeline design

Each step is a small module in `scripts/`, run as `python -m scripts.<step>`:

```
download -> validate -> preprocess -> analysis -> visualization
```

- **download** fetches public data. It is the only step that touches the
  network, and it is idempotent.
- **validate** is the gatekeeper: hard failures stop the pipeline before a
  bad input can contaminate results.
- **preprocess** cleans and joins, and applies CPI inflation adjustment.
  Processed tables live in `data/processed/`.
- **analysis** computes all statistics and writes a single machine-readable
  artifact (`outputs/results.json`). Analysis modules do not write prose.
- **visualization** renders figures from processed data.

Separating *analysis* (numbers) from *visualization* (figures) keeps the
article able to quote `results.json` directly, and lets figures be regenerated
without rerunning the statistics.

## Why results.json is the single source of truth

Data journalism fails when prose and data drift. Here the article (`index.qmd`)
imports `results.json` in a hidden code chunk and formats numbers inline, so a
change in the data pipeline automatically updates the published prose.

## Version control

Raw downloads are git-ignored (`.gitignore`): they total ~0.5 GB, they are
always fetchable via `scripts.download`, and the Scorecard server refuses
GitHub's cloud IPs (HTTP 403), so they could not be fetched by CI even if we
wanted to. To keep the GitHub Pages build network-free and reproducible, the
*derived* artifacts — `data/processed/`, `outputs/`, `figures/` — ARE
committed. Refresh them with `make pipeline` and commit the diff.

## Extensibility

- Adding a school: add its exact `INSTNM` to `PEER_SCHOOLS` in
  `scripts/config.py`.
- Adding a metric: add the raw column to `RAW_COLUMNS` (plus `PERCENT_COLUMNS`
  / `DOLLAR_COLUMNS` as appropriate), validate, and extend
  `scripts/analysis.py`.
- Changing the inflation reference year: edit `CPI_REFERENCE_YEAR`.
