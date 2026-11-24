# The Price of Prestige

> A data-journalism investigation into Stanford's published tuition, financial aid, student costs, and graduate earnings using College Scorecard and Bureau of Labor Statistics data.

**Live report:** [aayanahmed200.github.io/stanford-daily-price-of-prestige](https://aayanahmed200.github.io/stanford-daily-price-of-prestige/)

**Stanford Daily series:** [PlasticList EDA](https://aayanahmed200.github.io/stanford-daily-plasticlist-eda/) · [Blotter Fiction](https://aayanahmed200.github.io/stanford-daily-blotter-fiction/) · [ICE Extraction Pipeline](https://aayanahmed200.github.io/stanford-daily-biglocal-ice-pipeline/)

[![Python](https://img.shields.io/badge/python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/) [![Pandas](https://img.shields.io/badge/pandas-150458?style=for-the-badge&logo=pandas&logoColor=white)](https://pandas.pydata.org/) [![Plotly](https://img.shields.io/badge/plotly-3F4F75?style=for-the-badge&logo=plotly&logoColor=white)](https://plotly.com/) [![Quarto](https://img.shields.io/badge/quarto-75AADB?style=for-the-badge&logo=quarto&logoColor=white)](https://quarto.org/) [![Sass](https://img.shields.io/badge/sass-CC6699?style=for-the-badge&logo=sass&logoColor=white)](https://sass-lang.com/) [![GitHub Actions](https://img.shields.io/badge/github%20actions-2088FF?style=for-the-badge&logo=githubactions&logoColor=white)](https://github.com/features/actions)

## Overview

The project compares Stanford's published sticker price with estimated net prices after financial aid, examines how net price varies across family-income bands, and places graduate earnings and debt alongside the cost of attendance. It also compares Stanford with peer institutions and explores associations between earnings, price, selectivity, Pell share, and family income.

The article is generated from committed analysis outputs, so its figures and reported values can be traced back to the data pipeline rather than maintained as unrelated hard-coded numbers.

## Key findings covered

- Published sticker price and average net price, with net price broken down by family income.
- Median earnings ten years after entry and median student debt.
- Peer-school comparisons and a regression exploring the relationship between earnings and institutional and student characteristics.
- Downloaded, processed, and validated data artifacts used by the article and figures.

## Implementation

The project uses Python 3.12 and Quarto. Scripts download College Scorecard tables and the BLS inflation series, preprocess the data, calculate statistics, validate outputs, and generate figure data and result artifacts. The Quarto article in `index.qmd` reads from those generated artifacts. Plotly produces interactive figures; Sass and Quarto styling provide the report presentation.

GitHub Actions runs the Python tests and Ruff checks, renders the site, and publishes it to GitHub Pages when changes are pushed to `main`.

## Repository structure

- `index.qmd` — the article source; its figures and reported values read from generated outputs.
- `scripts/` — download, preprocessing, analysis, statistics, validation, and plotting code.
- `data/` — source and processed data used by the pipeline.
- `figures/` and `outputs/` — generated figures, tables, validation reports, and result artifacts.
- `notebooks/` — the companion analysis notebook.
- `_quarto.yml` and `assets/` — Quarto site configuration and shared series styling.
- `tests/` — pytest coverage for preprocessing, statistics, validation, and helpers.

## Run locally

1. Install the Python dependencies with `python -m pip install -r requirements.txt`.
2. Install the [Quarto CLI](https://quarto.org/docs/get-started/).
3. Render the article from the repository root:

```bash
quarto render index.qmd
```

The committed processed data and output artifacts allow the article to be rendered without repeating every source-data download.

## Status and limitations

The results depend on the source datasets, reporting periods, institutional definitions, and analysis choices used in the project. The regression is observational: it does not show that tuition, selectivity, Pell share, or family income causes differences in graduate earnings. Source data remains subject to the terms of its providers.

## License

MIT. See [LICENSE](LICENSE).
