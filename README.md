# Stanford Daily: The Price of Prestige

**Live:** [aayanahmed200.github.io/stanford-daily-price-of-prestige](https://aayanahmed200.github.io/stanford-daily-price-of-prestige/)

**Series:** [PlasticList](https://aayanahmed200.github.io/stanford-daily-plasticlist-eda/) · [Blotter fiction](https://aayanahmed200.github.io/stanford-daily-blotter-fiction/) · [ICE pipeline](https://aayanahmed200.github.io/stanford-daily-biglocal-ice-pipeline/)

[![Python](https://img.shields.io/badge/python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/) [![Pandas](https://img.shields.io/badge/pandas-150458?style=for-the-badge&logo=pandas&logoColor=white)](https://pandas.pydata.org/) [![Plotly](https://img.shields.io/badge/plotly-3F4F75?style=for-the-badge&logo=plotly&logoColor=white)](https://plotly.com/) [![Quarto](https://img.shields.io/badge/quarto-75AADB?style=for-the-badge&logo=quarto&logoColor=white)](https://quarto.org/) [![Sass](https://img.shields.io/badge/sass-CC6699?style=for-the-badge&logo=sass&logoColor=white)](https://sass-lang.com/) [![GitHub Actions](https://img.shields.io/badge/github%20actions-2088FF?style=for-the-badge&logo=githubactions&logoColor=white)](https://github.com/features/actions)

A data-journalism investigation into Stanford tuition, financial aid, student costs, and graduate earnings.

## Overview

The project compares student costs after financial aid with published tuition, then examines earnings and debt after graduation. It uses U.S. Department of Education data, inflation adjustments from the Bureau of Labor Statistics, and peer-school comparisons.

## How it was made

Built with Python 3.12 and Quarto. `scripts/` downloads the College Scorecard tables and the BLS inflation series, cleans them into `data/processed/`, computes the article's statistics, and writes `outputs/results.json` together with the figure tables and a validation report. The article in `index.qmd` reads every number from those artifacts rather than carrying hard-coded figures, so a re-run of the pipeline updates the prose as well as the charts.

Figures are drawn with Plotly and the report styling is Sass compiled through Quarto. The site is rendered with no navbar, sidebar or table of contents, because the other three pages in the series have none; `assets/series.css` is the shared series stylesheet and `assets/quarto.scss` only bridges Quarto's markup onto it. A GitHub Actions workflow renders the site and publishes it to GitHub Pages on push to `main`, while CI runs pytest and Ruff over the scripts.

## Highlights

- Reports a published sticker price of $87,833 and an average net price of $13,807.
- Average net price varies by family income, including a reported negative net price for families earning under $30,000 and $53,882 for families earning $110,001 or more.
- Reports median earnings of $124,080 ten years after entry and median debt of $12,000.
- Includes a regression analysis of earnings against price, selectivity, Pell share, and family income.

## Repository contents

- `index.qmd` — the article, with every number pulled from `outputs/results.json`.
- `scripts/` — download, preprocessing, analysis, statistics, validation and plotting modules.
- `data/processed/` — the derived tables the article and figures read.
- `figures/`, `outputs/` — committed figures, tables and result artifacts.
- `notebooks/notebook.qmd` — the analysis notebook linked from the site.
- `_quarto.yml`, `assets/quarto.scss` — site configuration and the report stylesheet.
- `tests/` — pytest checks for preprocessing, statistics, validation and helpers.

## Notes and limitations

The findings depend on the source datasets, reporting periods, definitions, and analysis choices used in this project. The regression is observational and should not be interpreted as evidence that the factors examined cause differences in earnings. Processed data, figures and result artifacts are committed so the article renders without repeating the full download step. Source data remains subject to the terms of its providers.

## License

MIT — see `LICENSE`.
