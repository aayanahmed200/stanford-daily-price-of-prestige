# Stanford Daily: The Price of Prestige

**[Read the live article](https://aayanahmed200.github.io/stanford-daily-price-of-prestige/)**

[![Python](https://img.shields.io/badge/python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Pandas](https://img.shields.io/badge/pandas-150458?style=for-the-badge&logo=pandas&logoColor=white)](https://pandas.pydata.org/)
[![Plotly](https://img.shields.io/badge/plotly-3F4F75?style=for-the-badge&logo=plotly&logoColor=white)](https://plotly.com/)
[![Sass](https://img.shields.io/badge/sass-CC6699?style=for-the-badge&logo=sass&logoColor=white)](https://sass-lang.com/)
[![GitHub Actions](https://img.shields.io/badge/github%20actions-2088FF?style=for-the-badge&logo=githubactions&logoColor=white)](https://github.com/features/actions)

**What a Stanford degree is actually worth** — a data-journalism investigation
into the price, aid, and earnings that come with a Stanford education, built on
the U.S. Department of Education's [College Scorecard](https://collegescorecard.ed.gov/)
and inflation-adjusted using the BLS Consumer Price Index.

![Net price by family income: Stanford vs. its peers](./figures/fig_aid_curve.png)

## Why this exists

Stanford's headline sticker price gets quoted on its own all the time, without
the context of what students actually end up paying, what they earn afterward,
or how that compares to peer institutions. This project pulls the same
government data any journalist can access and works out what the degree
actually costs and returns, across the income distribution rather than as a
single average.

Published as a full feature article:

**→ [Read the article](https://aayanahmed200.github.io/stanford-daily-price-of-prestige/)**
(plus the [analysis notebook](https://aayanahmed200.github.io/stanford-daily-price-of-prestige/notebooks/notebook.html))

## The data

| Source | What | Used for |
| --- | --- | --- |
| [College Scorecard](https://collegescorecard.ed.gov/) (June 2026 release) | Most-recent-cohort institution file + 1996-97..2025-26 historical archive | Cross-sectional analysis and the 30-year cost trend |
| FRED / BLS (CPIAUCSL) | Monthly CPI-U, seasonally adjusted | Expressing all dollars in 2025 dollars |
| [Chetty et al., "Mobility Report Cards" (NBER/Opportunity Insights)](https://opportunityinsights.org/paper/mrc/) | Tax-record-based study of family income and outcomes at "Ivy-Plus" colleges | Independent context on income access, cited in [Sources](docs/sources.qmd) |

Full citations: [`docs/sources.qmd`](docs/sources.qmd).

The analysis universe is 2,379 four-year, degree-granting non-profit schools.
Stanford is compared against 16 elite private peers; the earnings/ROI
regression uses 1,079 schools with matched earnings and cost data. Every
statistic in the article is read from `outputs/results.json`, so prose cannot
drift out of sync with the data.

The raw downloads (~0.5 GB) are not committed: `scripts.download` fetches them
from the U.S. Department of Education and FRED, and the Scorecard server blocks
GitHub's cloud IPs, so CI can't reach it either. Instead, the *derived*
artifacts (`data/processed/`, `outputs/`, `figures/`) are committed so the site
builds on Pages without network access. Refresh them with `make pipeline` (or
`make release-data`) and commit the changes.

## Key findings

- **Expensive on paper, affordable in practice.** Stanford's sticker price is
  $87,833 — 2.8x the national median of $31,112. But the *average net price*
  students actually pay is **$13,807**, *below* the national median of $22,347.
  Families earning under $30,000 pay a **negative** net price: aid exceeds the
  full cost of attendance.
- **The middle class carries the cost.** Net price swings from negative for the
  poorest families to **$53,882** for those earning $110,001+ — a ~$56,000
  swing across the income distribution.
- **The earnings premium is real and partly inherited.** Median earnings ten
  years after entry are **$124,080**, ~2.4x the national median. Even after
  controlling for price, selectivity, Pell share, and family income, Stanford
  graduates out-earn the model's prediction by roughly **47%**.
- **Graduates borrow little.** Median debt is **$12,000** (low-income
  graduates: $6,500) versus a national median of $22,300.
- **Tuition has outpaced inflation — but not unusually so.** Published tuition
  rose from $24,716 (2000-01) to $65,910 (2024-25) in 2025 dollars, roughly in
  line with peer elite privates (+48% vs +46%).

## Tech stack

- Python 3.12, [Quarto](https://quarto.org/) 1.10 (article, notebook, and site rendering)
- `pandas` / statistical analysis in `scripts/analysis.py`
- `pytest` for tests, `ruff` for lint, `pre-commit` hooks
- GitHub Actions CI, GitHub Pages for the published site

## Project structure

```
index.qmd                  Feature article (Quarto; the site homepage)
notebooks/notebook.qmd     Reproducible analysis walkthrough (Quarto)
docs/                      Methods, design notes, glossary
scripts/                   The pipeline (download -> visualize)
  download.py              Fetch Scorecard + CPI data (idempotent)
  validate.py              Data-quality checks
  preprocess.py            Clean, merge, inflation-adjust
  analysis.py              Compute all statistics
  visualization.py         Render all figures
tests/                     Unit tests (no network access)
data/                      Raw downloads (git-ignored) + processed tables
figures/                   Generated charts
outputs/                   results.json + tables (the article's source of truth)
```

## Setup

```bash
pip install -r requirements.txt
make pipeline     # download -> validate -> preprocess -> analysis -> visualization
make render       # render the article + notebook to _site/
```

`make download` needs network access to the U.S. Department of Education and FRED,
which GitHub's cloud IPs are blocked from — the derived artifacts (`data/processed/`,
`outputs/`, `figures/`) are already committed, so `make render` and `pytest tests/` work
without it. See the [Makefile](Makefile) for the individual targets (`download`,
`validate`, `preprocess`, `analysis`, `visualization`, `tests`, `lint`, `render-article`,
`render-notebook`, `clean`).

## Status

Data pipeline, analysis, notebook, and site are complete and live on GitHub
Pages. `tests/` covers the pipeline with no network access required; run with
`pytest tests/`. Not yet submitted to *The Stanford Daily* — see below for
what that requires and what's still open.

### Publication status (Stanford Daily Tech Bootcamp final project)

The bootcamp's final-project brief sets three requirements for publishing with
*The Stanford Daily*: article format (title, slug, authors, content), data
analysis, and three sources. Per that brief, AI may be used for the data
analysis and pipeline code in `scripts/` and `notebooks/notebook.qmd` — not for
writing `index.qmd`'s article text, which The Daily reviews for exactly that.

| Requirement | Status |
| --- | --- |
| Title | Set (`index.qmd` front matter) |
| Slug | Not yet assigned |
| Authors | `index.qmd` currently lists "Stanford Daily Tech Bootcamp"; needs real bylines before submission |
| Article content | Drafted in `index.qmd`; still needs to move to a Google Doc for DE/ME review before publication |
| Data analysis | Done — `scripts/`, `notebooks/notebook.qmd` |
| Three sources | Done — College Scorecard, BLS/FRED CPI, and Chetty et al. (NBER/Opportunity Insights); see [`docs/sources.qmd`](docs/sources.qmd) |

Reference piece from the workshop: Stanford Daily Community Voices, ["What 15
years of Daily opinion pieces reveal about
diversity"](https://stanforddaily.com/2025/11/05/from-the-community-more-diversity-rhetoric-fewer-diverse-ideas-what-15-years-of-daily-opinion-pieces-reveal/),
*The Stanford Daily*, Nov. 5, 2025.

## License

MIT — see [LICENSE](LICENSE). Data belongs to the U.S. Department of Education
and the U.S. Bureau of Labor Statistics.

*Stanford Daily: The Price of Prestige* was produced for the [Stanford Daily Tech
Bootcamp](https://github.com/TheStanfordDaily/tech-practicum).
