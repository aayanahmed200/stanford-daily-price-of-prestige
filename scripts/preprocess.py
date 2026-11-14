# ==============================================================================
# The Price of Prestige
# Step 3 - clean and feature-engineer the data
# ==============================================================================

"""Clean the raw inputs and build the analysis datasets.

Responsibilities:

* Coerce Scorecard strings (``NULL`` / ``PrivacySuppressed``) to ``NaN`` and
  enforce numeric types.
* Restrict to the analysis universe (four-year, non-profit institutions).
* Attach the peer-group and income-bucket labels used by the charts.
* Inflation-adjust dollars to real 2025 dollars using CPI-U.
* Assemble the long-run cost trend (focal schools, peer median, national
  median) from the historical archive.
* Persist clean tables to ``data/processed`` plus a cleaning report JSON.
"""

from __future__ import annotations

import argparse
import sys

import numpy as np
import pandas as pd

from scripts import config
from scripts.helpers import (
    dump_json,
    ensure_dir,
    get_logger,
    to_numeric,
)

log = get_logger("preprocess")


# ---------------------------------------------------------------------------
# CPI
# ---------------------------------------------------------------------------


def load_cpi_annual() -> pd.DataFrame:
    """Return a DataFrame of calendar-year average CPI-U (``year``, ``cpi``)."""
    cpi = pd.read_csv(config.CPI_CSV)
    date_col = "DATE" if "DATE" in cpi.columns else "observation_date"
    cpi = cpi.rename(columns={date_col: "date"})
    cpi["date"] = pd.to_datetime(cpi["date"])
    cpi["year"] = cpi["date"].dt.year
    cpi["cpi"] = pd.to_numeric(cpi["CPIAUCSL"], errors="coerce")
    annual = cpi.groupby("year", as_index=False)["cpi"].mean().dropna()
    return annual


def real_factor(cpi_annual: pd.DataFrame, ref_year: int) -> pd.Series:
    """Multipliers converting year-dollar values to ``ref_year`` dollars."""
    ref = float(cpi_annual.loc[cpi_annual["year"] == ref_year, "cpi"].iloc[0])
    factor = ref / cpi_annual["cpi"]
    return pd.Series(factor.values, index=cpi_annual["year"].values)


# ---------------------------------------------------------------------------
# Cleaning
# ---------------------------------------------------------------------------


def clean_institution() -> pd.DataFrame:
    """Load and clean the most-recent institution file."""
    raw = pd.read_csv(
        config.MOST_RECENT_CSV,
        usecols=config.RAW_COLUMNS,
        encoding="utf-8-sig",
        low_memory=False,
    )
    raw["INSTNM"] = raw["INSTNM"].astype("string").str.strip()
    raw["_key"] = raw["INSTNM"].str.lower()

    for col in config.DOLLAR_COLUMNS | config.PERCENT_COLUMNS:
        raw[col] = to_numeric(raw[col])
    for col in config.INTEGER_COLUMNS:
        raw[col] = to_numeric(raw[col]).astype("Int64")

    return raw


def filter_universe(df: pd.DataFrame) -> pd.DataFrame:
    """Keep four-year, degree-granting, non-profit institutions."""
    out = df[
        (df["HIGHDEG"] >= config.HIGHDEG_MIN) & (df["CONTROL"].isin(config.CONTROL_SET))
    ].copy()
    log.info("analysis universe: %d of %d institutions", len(out), len(df))
    return out


def build_peer_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Extract rows for the focal school and its peers (exact-name match)."""
    keys = {s.lower() for s in config.PEER_SCHOOLS}
    peers = df[df["_key"].isin(keys)].copy()
    peers["is_stanford"] = peers["INSTNM"] == config.FOCAL_SCHOOL
    peers = peers.sort_values(["is_stanford", "INSTNM"], ascending=[False, True])
    log.info(
        "peer frame: %d schools (%d including Stanford)",
        len(peers),
        int(peers["is_stanford"].sum()),
    )
    return peers


# ---------------------------------------------------------------------------
# Feature engineering
# ---------------------------------------------------------------------------


def add_income_bucket_rows(peers: pd.DataFrame) -> pd.DataFrame:
    """Melt net-price-by-income columns into a long ``aid curve`` table."""
    id_vars = ["UNITID", "INSTNM", "is_stanford"]
    cols = [id_vars, list(config.INCOME_BUCKETS)]
    long = peers[sum(cols, [])].melt(
        id_vars=id_vars,
        value_vars=list(config.INCOME_BUCKETS),
        var_name="bucket_col",
        value_name="net_price",
    )
    long["income_bucket"] = long["bucket_col"].map(config.INCOME_BUCKETS)
    long = long.dropna(subset=["net_price"]).copy()
    long["is_stanford"] = long["is_stanford"].astype(bool)
    return long


def add_real_dollars(df: pd.DataFrame, cpi_annual: pd.DataFrame) -> pd.DataFrame:
    """Append ``real_*`` columns expressing dollar columns in 2025 dollars.

    The most-recent cohort's costs describe the 2024-25 academic year; we
    convert using the 2024 CPI so the trend and cross-section are comparable.
    """
    factors = real_factor(cpi_annual, config.CPI_REFERENCE_YEAR)
    cpi_2024 = float(factors.loc[2024])
    out = df.copy()
    for col in config.DOLLAR_COLUMNS:
        out[f"real_{col}"] = out[col] * cpi_2024
    return out


# ---------------------------------------------------------------------------
# Cost trend
# ---------------------------------------------------------------------------


def build_cost_trend(cpi_annual: pd.DataFrame) -> pd.DataFrame:
    """Assemble the per-year cost series for the focal school and benchmarks."""
    trend = pd.read_csv(config.RAW_DIR / "trend_focus.csv", encoding="utf-8-sig")
    trend["year_int"] = trend["year"].str[:4].astype(int)
    for col in ["COSTT4_A", "TUITIONFEE_IN", "CONTROL"]:
        trend[col] = to_numeric(trend[col])

    # Benchmarks: peer set (private non-profits) and the national four-year
    # non-profit universe.
    peer_keys = {s.lower() for s in config.PEER_SCHOOLS if s != config.FOCAL_SCHOOL}
    trend["_key"] = trend["INSTNM"].astype("string").str.lower()
    trend["is_peer"] = trend["_key"].isin(peer_keys)
    trend["is_stanford"] = trend["_key"] == config.FOCAL_SCHOOL.lower()
    trend["is_national"] = (trend["CONTROL"].isin(config.CONTROL_SET)) & (
        ~trend["is_peer"] & ~trend["is_stanford"]
    )

    rows: list[dict] = []
    factors = real_factor(cpi_annual, config.CPI_REFERENCE_YEAR)
    for year_int, grp in trend.groupby("year_int"):
        cpi_ratio = float(factors.loc[year_int]) if year_int in factors.index else np.nan
        stan = grp[grp["is_stanford"]]
        peers = grp[grp["is_peer"]]
        nat = grp[grp["is_national"]]
        row = {
            "year_int": int(year_int),
            "year_label": f"{year_int}-{str(year_int + 1)[-2:]}",
            "cpi_ratio": cpi_ratio,
            "stanford_tuition": _first(stan, "TUITIONFEE_IN"),
            "stanford_cost": _first(stan, "COSTT4_A"),
            "peer_median_tuition": peers["TUITIONFEE_IN"].median(),
            "peer_median_cost": peers["COSTT4_A"].median(),
            "national_median_tuition": nat["TUITIONFEE_IN"].median(),
            "national_median_cost": nat["COSTT4_A"].median(),
            "n_peer": int(peers["UNITID"].nunique()),
            "n_national": int(nat["UNITID"].nunique()),
        }
        rows.append(row)

    out = pd.DataFrame(rows).sort_values("year_int")
    for col in [
        "stanford_tuition",
        "stanford_cost",
        "peer_median_tuition",
        "peer_median_cost",
        "national_median_tuition",
        "national_median_cost",
    ]:
        out[f"real_{col}"] = out[col] * out["cpi_ratio"]
    out = out.dropna(subset=["cpi_ratio"])
    log.info(
        "cost trend: %d years (%d..%d)",
        len(out),
        int(out["year_int"].min()),
        int(out["year_int"].max()),
    )
    return out


def _first(df: pd.DataFrame, col: str) -> float | np.nan:
    if df.empty:
        return np.nan
    return float(df[col].iloc[0])


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    _ = argparse.ArgumentParser(description=__doc__).parse_args(argv)

    try:
        ensure_dir(config.PROCESSED_DIR)
        cpi_annual = load_cpi_annual()

        raw = clean_institution()
        universe = filter_universe(raw)
        universe = add_real_dollars(universe, cpi_annual)
        peers = build_peer_frame(universe)
        aid_curve = add_income_bucket_rows(peers)
        cost_trend = build_cost_trend(cpi_annual)

        roi_sample = universe[
            universe["NPT4_PRIV"].notna()
            & universe["MD_EARN_WNE_P10"].notna()
            & (universe["COUNT_WNE_P10"] >= config.MIN_COUNT_WNE_P10)
        ].copy()

        # Persist.
        universe.to_csv(config.PROCESSED_SCORECARD, index=False)
        peers.to_csv(config.PROCESSED_PEERS, index=False)
        aid_curve.to_csv(config.PROCESSED_DIR / "aid_curve.csv", index=False)
        cost_trend.to_csv(config.PROCESSED_TREND, index=False)
        roi_sample.to_csv(config.PROCESSED_ROI, index=False)

        report = {
            "raw_rows": int(len(raw)),
            "universe_rows": int(len(universe)),
            "peer_rows": int(len(peers)),
            "roi_sample_rows": int(len(roi_sample)),
            "aid_curve_rows": int(len(aid_curve)),
            "cost_trend_years": int(len(cost_trend)),
            "n_peer_schools": int(peers["UNITID"].nunique()),
            "n_stanford_rows": int(peers["is_stanford"].sum()),
            "missing_after_clean": {
                c: round(float(universe[c].isna().mean()), 4) for c in config.DOLLAR_COLUMNS
            },
        }
        dump_json(config.OUTPUTS_DIR / "cleaning_report.json", report)
        log.info("preprocess complete: %s", report)
        return 0
    except Exception as exc:  # noqa: BLE001
        log.error("preprocess step failed: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
