# The Price of Prestige

A data-journalism investigation of Stanford's published cost, the price students pay after financial aid, and graduate outcomes, using U.S. Department of Education College Scorecard data.

**[Read the published article](https://aayanahmed200.github.io/stanford-daily-price-of-prestige/)**

## Overview

The analysis compares Stanford's sticker price with average net price and net price by family income. It also examines graduation, student debt and earnings, and places Stanford alongside a peer group of 15 other private universities. The analysis includes inflation adjustments and a regression exploring associations between earnings and institutional measures.

## Repository contents

- `index.qmd` — the published article and its data-driven narrative.
- `scripts/` — data download, validation, preprocessing, analysis and visualisation steps.
- `data/` — raw inputs and processed datasets. Raw downloads are not committed; derived data is.
- `outputs/` and `figures/` — machine-readable results, tables and charts used by the article.
- `notebooks/` and `docs/` — exploratory work, methods, sources and project notes.
- `tests/` — checks for data processing and analytical functions.

## Technology

Python 3.11+, pandas, Plotly and Quarto. The test and lint setup uses pytest and Ruff. Quarto is a separate installation; Python packages are listed in `requirements.txt` and the development extras in `pyproject.toml`.

## Run locally

Install the Python dependencies and development tools:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e ".[dev]"
```

Run the full data pipeline and render the article:

```bash
make pipeline
make render
```

The first pipeline run downloads the source data and can require roughly 0.5 GB of disk space. The committed processed data, results and figures let you render the article without downloading the raw files again.

Run checks with:

```bash
make tests
make lint
```

## Scope and limitations

The reported figures reflect the College Scorecard release, cohort definitions, inflation reference year and peer group recorded in the project outputs. The regression is observational: it describes associations and does not show that price, selectivity or another measured factor causes higher or lower earnings. Net price and earnings figures should be read with their source definitions and reporting periods.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for the full text.
