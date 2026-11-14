# Stanford Daily: The Price of Prestige

**[Read the article](https://aayanahmed200.github.io/stanford-daily-price-of-prestige/)**

[![Python](https://img.shields.io/badge/python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/) [![Pandas](https://img.shields.io/badge/pandas-150458?style=for-the-badge&logo=pandas&logoColor=white)](https://pandas.pydata.org/) [![Plotly](https://img.shields.io/badge/plotly-3F4F75?style=for-the-badge&logo=plotly&logoColor=white)](https://plotly.com/) [![Sass](https://img.shields.io/badge/sass-CC6699?style=for-the-badge&logo=sass&logoColor=white)](https://sass-lang.com/) [![GitHub Actions](https://img.shields.io/badge/github%20actions-2088FF?style=for-the-badge&logo=githubactions&logoColor=white)](https://github.com/features/actions)

A data-journalism investigation into Stanford tuition, financial aid, student costs, and graduate earnings.

## Overview

The project compares student costs after financial aid with published tuition, then examines earnings and debt after graduation. It uses U.S. Department of Education data, inflation adjustments from the Bureau of Labor Statistics, and peer-school comparisons.

## Highlights

- Reports a published sticker price of $87,833 and an average net price of $13,807.
- Average net price varies by family income, including a reported negative net price for families earning under $30,000 and $53,882 for families earning $110,001 or more.
- Reports median earnings of $124,080 ten years after entry and median debt of $12,000.
- Includes a regression analysis of earnings against price, selectivity, Pell share, and family income.

## Technology

Python 3.12, Quarto, pandas, Plotly, pytest, Ruff, and GitHub Actions.

## Run locally

```bash
pip install -r requirements.txt
make pipeline
make render
```

Raw downloads come from the Department of Education and FRED. Processed data, figures, and result artifacts are included so rendering and tests do not require repeating the full download step.

## Notes and limitations

The findings depend on the source datasets, reporting periods, definitions, and analysis choices used in this project. The regression is observational and should not be interpreted as evidence that the factors examined cause differences in earnings. Source data remains subject to the terms of its providers.

## License

MIT — see `LICENSE`.