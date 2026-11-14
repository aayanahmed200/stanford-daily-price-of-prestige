# ==============================================================================
# The Price of Prestige
# Project configuration: paths, data sources, analysis parameters.
# ==============================================================================

"""Central configuration for the Price of Prestige project.

Every constant used by the pipeline lives here so the analysis is fully
reproducible and easy to audit. Paths are resolved relative to the repository
root (the directory that contains ``pyproject.toml``).
"""

from __future__ import annotations

import datetime as _dt
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
EXTERNAL_DIR = DATA_DIR / "external"

FIGURES_DIR = PROJECT_ROOT / "figures"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
ASSETS_DIR = PROJECT_ROOT / "assets"
NOTEBOOKS_DIR = PROJECT_ROOT / "notebooks"

# ---------------------------------------------------------------------------
# Data sources
# ---------------------------------------------------------------------------

# U.S. Department of Education, College Scorecard (updated June 2026).
# "Most Recent Cohorts" institution-level file.
MOST_RECENT_ZIP_URL = (
    "https://ed-public-download.scorecard.network/downloads/"
    "Most-Recent-Cohorts-Institution_06102026.zip"
)
MOST_RECENT_ZIP = RAW_DIR / "Most-Recent-Cohorts-Institution_06102026.zip"
MOST_RECENT_CSV = RAW_DIR / "Most-Recent-Cohorts-Institution.csv"

# Full historical Scorecard data (institution-level files 1996-97..2025-26).
RAW_DATA_ZIP_URL = (
    "https://ed-public-download.scorecard.network/downloads/College_Scorecard_Raw_Data_06102026.zip"
)
RAW_DATA_ZIP = RAW_DIR / "College_Scorecard_Raw_Data_06102026.zip"
RAW_DATA_INNER_DIR = "College_Scorecard_Raw_Data_06032026"

# Bureau of Labor Statistics CPI-U (All Urban Consumers, all items, seasonally
# adjusted), served as CSV by the St. Louis Fed FRED service.
CPI_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=CPIAUCSL"
CPI_CSV = RAW_DIR / "cpi.csv"

# Focal cohort: every academic year file shipped in the raw data zip.
TREND_YEAR_FILES = [
    "MERGED1996_97_PP.csv",
    "MERGED1997_98_PP.csv",
    "MERGED1998_99_PP.csv",
    "MERGED1999_00_PP.csv",
    "MERGED2000_01_PP.csv",
    "MERGED2001_02_PP.csv",
    "MERGED2002_03_PP.csv",
    "MERGED2003_04_PP.csv",
    "MERGED2004_05_PP.csv",
    "MERGED2005_06_PP.csv",
    "MERGED2006_07_PP.csv",
    "MERGED2007_08_PP.csv",
    "MERGED2008_09_PP.csv",
    "MERGED2009_10_PP.csv",
    "MERGED2010_11_PP.csv",
    "MERGED2011_12_PP.csv",
    "MERGED2012_13_PP.csv",
    "MERGED2013_14_PP.csv",
    "MERGED2014_15_PP.csv",
    "MERGED2015_16_PP.csv",
    "MERGED2016_17_PP.csv",
    "MERGED2017_18_PP.csv",
    "MERGED2018_19_PP.csv",
    "MERGED2019_20_PP.csv",
    "MERGED2020_21_PP.csv",
    "MERGED2021_22_PP.csv",
    "MERGED2022_23_PP.csv",
    "MERGED2023_24_PP.csv",
    "MERGED2024_25_PP.csv",
    "MERGED2025_26_PP.csv",
]

# CPI reference month used to express all dollars in "real" 2025 dollars.
CPI_REFERENCE_YEAR = 2025

# ---------------------------------------------------------------------------
# Analysis universe
# ---------------------------------------------------------------------------

# Stanford plus the peer institutions it is most frequently benchmarked
# against (the Ivy League, peer privates, and the two elite technical
# institutes). Names are matched exactly against the Scorecard INSTNM field.
PEER_SCHOOLS = [
    "Stanford University",
    "Harvard University",
    "Yale University",
    "Princeton University",
    "Massachusetts Institute of Technology",
    "California Institute of Technology",
    "Columbia University in the City of New York",
    "University of Pennsylvania",
    "Brown University",
    "Dartmouth College",
    "Cornell University",
    "University of Chicago",
    "Northwestern University",
    "Johns Hopkins University",
    "Rice University",
    "Carnegie Mellon University",
]

FOCAL_SCHOOL = "Stanford University"

# Scorecard income brackets used for net-price-by-family-income (private
# non-profit institutions, dependent students). Values are average net price
# (cost of attendance minus grants and scholarships).
INCOME_BUCKETS = {
    "NPT41_PRIV": "$0\u201330,000",
    "NPT42_PRIV": "$30,001\u201348,000",
    "NPT43_PRIV": "$48,001\u201375,000",
    "NPT44_PRIV": "$75,001\u2013110,000",
    "NPT45_PRIV": "$110,001+",
}

# Columns read from the most-recent institution file (kept deliberately small
# to keep the pipeline fast and auditable).
RAW_COLUMNS = [
    "UNITID",
    "INSTNM",
    "STABBR",
    "CITY",
    "CONTROL",
    "HIGHDEG",
    "CCBASIC",
    "ADM_RATE",
    "SAT_AVG",
    "UGDS",
    "PCTPELL",
    "DEP_INC_AVG",
    "PAR_ED_PCT_1STGEN",
    "COSTT4_A",
    "TUITIONFEE_IN",
    "NPT4_PRIV",
    "NPT41_PRIV",
    "NPT42_PRIV",
    "NPT43_PRIV",
    "NPT44_PRIV",
    "NPT45_PRIV",
    "C150_4",
    "RET_FT4",
    "GRAD_DEBT_MDN",
    "LO_INC_DEBT_MDN",
    "HI_INC_DEBT_MDN",
    "FIRSTGEN_DEBT_MDN",
    "RPY_3YR_RT",
    "MD_EARN_WNE_P10",
    "PCT25_EARN_WNE_P10",
    "PCT75_EARN_WNE_P10",
    "PCT90_EARN_WNE_P10",
    "COUNT_WNE_P10",
]

# Columns that should be treated as numeric percentages/rates (0-1 scale).
PERCENT_COLUMNS = {
    "ADM_RATE",
    "PCTPELL",
    "PAR_ED_PCT_1STGEN",
    "C150_4",
    "RET_FT4",
    "RPY_3YR_RT",
}

DOLLAR_COLUMNS = {
    "DEP_INC_AVG",
    "COSTT4_A",
    "TUITIONFEE_IN",
    "NPT4_PRIV",
    "NPT41_PRIV",
    "NPT42_PRIV",
    "NPT43_PRIV",
    "NPT44_PRIV",
    "NPT45_PRIV",
    "GRAD_DEBT_MDN",
    "LO_INC_DEBT_MDN",
    "HI_INC_DEBT_MDN",
    "FIRSTGEN_DEBT_MDN",
    "MD_EARN_WNE_P10",
    "PCT25_EARN_WNE_P10",
    "PCT75_EARN_WNE_P10",
    "PCT90_EARN_WNE_P10",
}

INTEGER_COLUMNS = {"UNITID", "UGDS", "COUNT_WNE_P10"}

# The analysis universe: four-year, degree-granting institutions with a
# predominately bachelor's (or higher) focus, public or private non-profit.
HIGHDEG_MIN = 3  # 4 or more years
CONTROL_SET = (1, 2)  # public or private non-profit (exclude for-profit)

# A school enters the earnings/ROI sample only if it reports both a net price
# and median earnings, and enrolls a reasonably large cohort (data-quality
# floor set to 30 students with matched earnings records).
MIN_COUNT_WNE_P10 = 30

# Derived output files.
PROCESSED_SCORECARD = PROCESSED_DIR / "scorecard_clean.csv"
PROCESSED_PEERS = PROCESSED_DIR / "peer_comparison.csv"
PROCESSED_TREND = PROCESSED_DIR / "cost_trend.csv"
PROCESSED_ROI = PROCESSED_DIR / "roi_sample.csv"
RESULTS_JSON = OUTPUTS_DIR / "results.json"
RESULTS_DIR = OUTPUTS_DIR

# Random seed for all stochastic procedures (bootstrap, etc.).
RANDOM_SEED = 20260701

# Project metadata used by the article.
PUBLISHED_DATE = _dt.date(2026, 8, 4)
AUTHOR = "Stanford Daily Tech Bootcamp"
ARTICLE_TITLE = "The Price of Prestige: What a Stanford Degree Is Actually Worth"
