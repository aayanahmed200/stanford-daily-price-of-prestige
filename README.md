# Stanford Daily: The Price of Prestige

**[Read the article](https://aayanahmed200.github.io/stanford-daily-price-of-prestige/)**

[![Python](https://img.shields.io/badge/python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/) [![Pandas](https://img.shields.io/badge/pandas-150458?style=for-the-badge&logo=pandas&logoColor=white)](https://pandas.pydata.org/) [![Plotly](https://img.shields.io/badge/plotly-3F4F75?style=for-the-badge&logo=plotly&logoColor=white)](https://plotly.com/) [![Sass](https://img.shields.io/badge/sass-CC6699?style=for-the-badge&logo=sass&logoColor=white)](https://sass-lang.com/) [![GitHub Actions](https://img.shields.io/badge/github%20actions-2088FF?style=for-the-badge&logo=githubactions&logoColor=white)](https://github.com/features/actions)

A data-journalism investigation into Stanford's tuition, financial aid, student costs, and graduate earnings, using U.S. Department of Education data and inflation adjustments from the Bureau of Labor Statistics.

## Overview

The project compares what students pay after financial aid with published tuition, and examines earnings and debt after graduation. It uses a peer-school comparison and documents the limits of each dataset rather than relying on Stanford's sticker price alone.

## Highlights

- Stanford's published sticker price in the analysis is $87,833, while the reported average net price is $13,807.
- Average net price varies substantially by family income; the analysis reports negative net price for families earning under $30,000 and $53,882 for families earning $110,001 or more.
- Median earnings ten years after entry are reported as $124,080; median debt is $12,000.
- In the regression model, Stanford graduates' earnings are about 47% above the model prediction after controlling for price, selectivity, Pell share, and family income.

## Data and methodology

- **College Scorecard:** institution-level price, aid, debt, and earnings data, including a historical archive.
- **BLS/FRED CPI-U:** inflation adjustment to 2025 dollars.
- **Chetty et al., Mobility Report Cards:** external context on income access and outcomes at highly selective colleges.

The analysis covers 2,379 four-year non-profit institutions. The earnings comparison uses the subset with complete data for all model predictors. Full citations and calculations are documented in `docs/sources.qmd` and the Quarto article.

## Technology

Python 3.12, Quarto, pandas, Plotly, pytest, Ruff, and GitHub Actions.

## Run locally

```bash
pip install -r requirements.txt
make pipeline
make render
```

Raw downloads are fetched from the Department of Education and FRED and are not committed. Processed data, figures, and result artifacts are included, so rendering and tests can run without repeating the full download step. See the `Makefile` for individual targets.

## Notes and limitations

These are estimates based on the available cohorts and variables, not a guarantee of an individual student's cost or future earnings. The regression comparison is observational and should not be read as proof that attending one institution causes a specific earnings premium. Figures and article text are generated from `outputs/results.json` to keep reported values aligned with the analysis.

## License

MIT — see `LICENSE`. Source data remains the property and under the terms of the U.S. Department of Education, BLS, and other cited providers.
