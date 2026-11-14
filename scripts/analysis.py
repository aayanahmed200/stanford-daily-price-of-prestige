# ==============================================================================
# The Price of Prestige
# Step 4 - run the substantive analysis
# ==============================================================================

"""Compute every statistic and table quoted in the article.

The step reads the cleaned datasets produced by ``preprocess`` and writes:

* ``outputs/results.json``            -- the canonical machine-readable results
* ``outputs/tables/*.csv``            -- tidy tables for charts and appendices

Sections mirror the article's findings: sticker cost, the financial-aid curve,
student composition, debt, earnings, the ROI regression, and the long-run
cost trend.
"""

from __future__ import annotations

import argparse
import sys

import numpy as np
import pandas as pd

from scripts import config
from scripts.helpers import dump_json, ensure_dir, get_logger
from scripts.statistics import (
    add_focal_residual,
    annualized_growth,
    bootstrap_median_ci,
    cohens_d,
    mann_whitney,
    ols_robust,
)

log = get_logger("analysis")


def _pct(x: float | None) -> float | None:
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else x


def load_frames() -> dict[str, pd.DataFrame]:
    """Load all cleaned datasets produced by the preprocess step."""
    frames = {
        "universe": pd.read_csv(config.PROCESSED_SCORECARD),
        "peers": pd.read_csv(config.PROCESSED_PEERS),
        "aid_curve": pd.read_csv(config.PROCESSED_DIR / "aid_curve.csv"),
        "trend": pd.read_csv(config.PROCESSED_TREND),
        "roi": pd.read_csv(config.PROCESSED_ROI),
    }
    for name, df in frames.items():
        if df.empty:
            raise ValueError(f"cleaned dataset {name} is empty - run preprocess")
    return frames


# ---------------------------------------------------------------------------
# Findings
# ---------------------------------------------------------------------------


def focal_summary(peers: pd.DataFrame, universe: pd.DataFrame) -> dict:
    """Single-source summary of every number cited about Stanford."""
    row = peers[peers["INSTNM"] == config.FOCAL_SCHOOL].iloc[0]
    national = universe
    med = lambda s: float(s.median())  # noqa: E731
    out = {
        "unitid": int(row["UNITID"]),
        "sticker_cost": float(row["COSTT4_A"]),
        "tuition_fees": float(row["TUITIONFEE_IN"]),
        "net_price_avg": float(row["NPT4_PRIV"]),
        "grad_rate_150": float(row["C150_4"]),
        "retention": float(row["RET_FT4"]),
        "pell_share": float(row["PCTPELL"]),
        "firstgen_share": float(row["PAR_ED_PCT_1STGEN"]),
        "dep_income_avg": float(row["DEP_INC_AVG"]),
        "adm_rate": float(row["ADM_RATE"]),
        "sat_avg": float(row["SAT_AVG"]),
        "ugds": float(row["UGDS"]),
        "repay_3yr": float(row["RPY_3YR_RT"]),
        "grad_debt_median": float(row["GRAD_DEBT_MDN"]),
        "lowinc_debt_median": float(row["LO_INC_DEBT_MDN"]),
        "hiinc_debt_median": float(row["HI_INC_DEBT_MDN"]),
        "firstgen_debt_median": float(row["FIRSTGEN_DEBT_MDN"]),
        "earn_median_p10": float(row["MD_EARN_WNE_P10"]),
        "earn_p25_p10": float(row["PCT25_EARN_WNE_P10"]),
        "earn_p75_p10": float(row["PCT75_EARN_WNE_P10"]),
        "earn_p90_p10": float(row["PCT90_EARN_WNE_P10"]),
        "earn_count_p10": int(row["COUNT_WNE_P10"]),
        "net_price_by_income": {
            label: float(row[col]) for col, label in config.INCOME_BUCKETS.items()
        },
        "real_sticker_cost_2025": float(row["real_COSTT4_A"]),
        "real_net_price_2025": float(row["real_NPT4_PRIV"]),
    }
    # Context
    out["national"] = {
        "median_cost": med(national["COSTT4_A"]),
        "median_net_price": med(national["NPT4_PRIV"]),
        "median_earnings_p10": med(national["MD_EARN_WNE_P10"]),
        "median_grad_rate": med(national["C150_4"]),
        "median_grad_debt": med(national["GRAD_DEBT_MDN"]),
        "median_pell": med(national["PCTPELL"]),
    }
    out["multiples"] = {
        "cost_vs_national": out["sticker_cost"] / out["national"]["median_cost"],
        "net_price_vs_national": out["net_price_avg"] / out["national"]["median_net_price"],
        "earnings_vs_national": out["earn_median_p10"] / out["national"]["median_earnings_p10"],
    }
    return out


def rankings(peers: pd.DataFrame) -> dict:
    """Rank Stanford vs peers on the headline metrics."""
    # ascending=True ranks the *best* (lowest for cost-type metrics, highest
    # for outcome-type metrics) at position 0.
    metrics = {
        "NPT4_PRIV": ("net price (lower is better)", True),
        "COSTT4_A": ("sticker cost (lower is better)", True),
        "C150_4": ("graduation rate (higher is better)", False),
        "PCTPELL": ("Pell share (higher is better)", False),
        "GRAD_DEBT_MDN": ("median grad debt (lower is better)", True),
        "MD_EARN_WNE_P10": ("median earnings (higher is better)", False),
        "PCT90_EARN_WNE_P10": ("P90 earnings (higher is better)", False),
    }
    result: dict = {}
    for col, (label, asc) in metrics.items():
        ranked = peers.dropna(subset=[col]).sort_values(col, ascending=asc)
        ranked = ranked.reset_index(drop=True)
        positions = ranked.index[ranked["INSTNM"] == config.FOCAL_SCHOOL].tolist()
        rank = int(positions[0]) + 1 if positions else None
        result[col] = {
            "label": label,
            "rank": rank,
            "n": int(len(ranked)),
            "value": float(ranked.loc[ranked["INSTNM"] == config.FOCAL_SCHOOL, col].iloc[0])
            if rank is not None
            else None,
            "top": ranked["INSTNM"].head(3).tolist(),
            "best": ranked["INSTNM"].iloc[0],
            "worst": ranked["INSTNM"].iloc[-1],
        }
    return result


def aid_curve_stats(aid: pd.DataFrame, peers: pd.DataFrame) -> dict:
    """Median aid curve for peers and Stanford's values per income bucket."""
    buckets = list(config.INCOME_BUCKETS.values())
    stan = aid[aid["is_stanford"]].set_index("income_bucket")["net_price"].to_dict()
    peer_aid = aid[~aid["is_stanford"]]
    result: dict = {
        "buckets": buckets,
        "stanford": {},
        "peer_median": {},
        "peer_ci_low": {},
        "peer_ci_high": {},
        "n_peers": {},
    }
    for b in buckets:
        vals = peer_aid.loc[peer_aid["income_bucket"] == b, "net_price"]
        ci = bootstrap_median_ci(vals, n_boot=5000)
        result["stanford"][b] = stan.get(b)
        result["peer_median"][b] = float(vals.median())
        result["peer_ci_low"][b] = ci["ci_low"]
        result["peer_ci_high"][b] = ci["ci_high"]
        result["n_peers"][b] = int(vals.notna().sum())
    # Middle-class squeeze ratio: net price at $75-110k vs $0-30k (Stanford)
    p44 = stan.get("$75,001\u2013110,000")
    p41 = stan.get("$0\u201330,000")
    result["middle_class_squeeze"] = {
        "stanford_p44": p44,
        "stanford_p41": p41,
        "gap": (p44 - p41) if p44 is not None and p41 is not None else None,
        "peer_median_p44": result["peer_median"].get("$75,001\u2013110,000"),
        "peer_median_p41": result["peer_median"].get("$0\u201330,000"),
    }
    return result


def debt_stats(peers: pd.DataFrame, universe: pd.DataFrame) -> dict:
    """Debt by income group, Stanford vs peer median vs national."""
    row = peers[peers["INSTNM"] == config.FOCAL_SCHOOL].iloc[0]
    # Peer median must exclude Stanford itself -- it's the baseline Stanford
    # is being compared against, not a group Stanford is a member of. (Same
    # convention as hypothesis_tests()'s "others" and aid_curve_stats()'s
    # "peer_aid".)
    others = peers[peers["INSTNM"] != config.FOCAL_SCHOOL]
    result = {
        "stanford": {
            "grad_debt_median": float(row["GRAD_DEBT_MDN"]),
            "lowinc": float(row["LO_INC_DEBT_MDN"]),
            "hiinc": float(row["HI_INC_DEBT_MDN"]),
            "firstgen": float(row["FIRSTGEN_DEBT_MDN"]),
        },
        "peer_median": {
            "grad_debt_median": float(others["GRAD_DEBT_MDN"].median()),
            "lowinc": float(others["LO_INC_DEBT_MDN"].median()),
            "hiinc": float(others["HI_INC_DEBT_MDN"].median()),
            "firstgen": float(others["FIRSTGEN_DEBT_MDN"].median()),
        },
        "national_median": {
            "grad_debt_median": float(universe["GRAD_DEBT_MDN"].median()),
            "lowinc": float(universe["LO_INC_DEBT_MDN"].median()),
            "hiinc": float(universe["HI_INC_DEBT_MDN"].median()),
            "firstgen": float(universe["FIRSTGEN_DEBT_MDN"].median()),
        },
        "stanford_vs_national": {
            "grad_debt_ratio": float(row["GRAD_DEBT_MDN"])
            / float(universe["GRAD_DEBT_MDN"].median()),
        },
    }
    return result


def earnings_stats(peers: pd.DataFrame, universe: pd.DataFrame) -> dict:
    """Earnings percentiles, Stanford vs peer median vs national."""
    row = peers[peers["INSTNM"] == config.FOCAL_SCHOOL].iloc[0]
    # Exclude Stanford from its own comparison baseline (see debt_stats).
    others = peers[peers["INSTNM"] != config.FOCAL_SCHOOL]
    return {
        "stanford": {
            "median": float(row["MD_EARN_WNE_P10"]),
            "p25": float(row["PCT25_EARN_WNE_P10"]),
            "p75": float(row["PCT75_EARN_WNE_P10"]),
            "p90": float(row["PCT90_EARN_WNE_P10"]),
        },
        "peer_median": {
            "median": float(others["MD_EARN_WNE_P10"].median()),
            "p25": float(others["PCT25_EARN_WNE_P10"].median()),
            "p75": float(others["PCT75_EARN_WNE_P10"].median()),
            "p90": float(others["PCT90_EARN_WNE_P10"].median()),
        },
        "national_median": {
            "median": float(universe["MD_EARN_WNE_P10"].median()),
            "p25": float(universe["PCT25_EARN_WNE_P10"].median()),
            "p75": float(universe["PCT75_EARN_WNE_P10"].median()),
            "p90": float(universe["PCT90_EARN_WNE_P10"].median()),
        },
    }


def hypothesis_tests(peers: pd.DataFrame, universe: pd.DataFrame) -> dict:
    """Non-parametric comparisons: Stanford vs peers, and peers vs national."""
    stan = peers[peers["INSTNM"] == config.FOCAL_SCHOOL].iloc[0]
    others = peers[peers["INSTNM"] != config.FOCAL_SCHOOL]
    tests: dict = {}

    def run_focal(key: str, col: str) -> None:
        # A formal two-sample test (Mann-Whitney) doesn't work here: Stanford is a
        # single observation, and with n2 peers the smallest two-sided p-value the
        # test can ever produce is ~2/(n2+1) -- with ~15 peers that floor sits around
        # 0.13, well above the conventional 0.05 threshold. That means the test would
        # report "not statistically significant" unconditionally, regardless of how
        # extreme Stanford's actual value is, which would silently misrepresent a real
        # difference as a null result. A percentile rank against the peer distribution
        # is the honest way to say "how unusual is Stanford compared to its peers".
        val = float(stan[col])
        ref = others[col].dropna()
        percentile = float((ref < val).mean() * 100 + (ref == val).mean() * 50)
        tests[key] = {
            "stanford": val,
            "peer_median": float(ref.median()),
            "peer_percentile": percentile,
            "n_peers": int(len(ref)),
            "cohens_d": cohens_d(pd.Series([val]), ref),
        }

    for key, col in [
        ("net_price_avg", "NPT4_PRIV"),
        ("grad_debt", "GRAD_DEBT_MDN"),
        ("earn_median", "MD_EARN_WNE_P10"),
        ("pell_share", "PCTPELL"),
    ]:
        run_focal(key, col)

    # Peers vs national IS a proper two-sample comparison (both sides have real
    # sample sizes), so Mann-Whitney is valid and meaningful here.
    for key, col in [
        ("earn_median", "MD_EARN_WNE_P10"),
        ("sticker_cost", "COSTT4_A"),
        ("grad_debt", "GRAD_DEBT_MDN"),
    ]:
        mw = mann_whitney(others[col], universe[col])
        d = cohens_d(others[col], universe[col])
        tests[f"peers_vs_national_{key}"] = {
            "peer_median": float(others[col].median()),
            "national_median": float(universe[col].median()),
            "mann_whitney": mw,
            "cohens_d": d,
        }
    return tests


def roi_regression(roi: pd.DataFrame) -> dict:
    """Does the earnings premium survive controls? Robust OLS on the ROI sample."""
    d = roi.copy()
    d["log_earn"] = np.log(d["MD_EARN_WNE_P10"])
    d["log_adm"] = np.log(d["ADM_RATE"].clip(lower=1e-4))
    model = ols_robust(
        d,
        outcome="log_earn",
        predictors=["real_NPT4_PRIV", "SAT_AVG", "log_adm", "DEP_INC_AVG", "PCTPELL"],
    )
    model = add_focal_residual(
        model,
        d,
        "log_earn",
        ["real_NPT4_PRIV", "SAT_AVG", "log_adm", "DEP_INC_AVG", "PCTPELL"],
        log_outcome=True,
    )
    return model


def trend_stats(trend: pd.DataFrame) -> dict:
    """Long-run cost growth: nominal and real, Stanford/peers/national."""
    # The trend files have ragged coverage (tuition data start in 2000, total
    # cost in 2009), so each series computes its own first/last valid year.
    t = trend.sort_values("year_int")
    rows = []
    for key, nominal, real in [
        ("stanford", "stanford_tuition", "real_stanford_tuition"),
        ("peer_median", "peer_median_tuition", "real_peer_median_tuition"),
        ("national_median", "national_median_tuition", "real_national_median_tuition"),
    ]:
        sub = t.dropna(subset=[nominal])
        if len(sub) < 2:
            continue
        start, end = sub.iloc[0], sub.iloc[-1]
        years = end["year_int"] - start["year_int"]
        rows.append(
            {
                "series": key,
                "start_year": int(start["year_int"]),
                "end_year": int(end["year_int"]),
                "start_nominal": float(start[nominal]),
                "end_nominal": float(end[nominal]),
                "start_real": float(start[real]),
                "end_real": float(end[real]),
                "nominal_growth_pct": (end[nominal] / start[nominal] - 1) * 100,
                "real_growth_pct": (end[real] / start[real] - 1) * 100,
                "cagr_nominal": annualized_growth(start[nominal], end[nominal], years),
                "cagr_real": annualized_growth(start[real], end[real], years),
                "years": years,
            }
        )
    # Cost-of-attendance (total sticker) trend for Stanford where available.
    t2 = t.dropna(subset=["stanford_cost"])
    result = {
        "tuition_series": rows,
        "series_start": int(t.iloc[0]["year_int"]),
        "series_end": int(t.iloc[-1]["year_int"]),
    }
    if len(t2):
        s0, s1 = t2.iloc[0], t2.iloc[-1]
        yr = s1["year_int"] - s0["year_int"]
        result["stanford_total_cost"] = {
            "start_year": int(s0["year_int"]),
            "end_year": int(s1["year_int"]),
            "start_nominal": float(s0["stanford_cost"]),
            "end_nominal": float(s1["stanford_cost"]),
            "nominal_growth_pct": (s1["stanford_cost"] / s0["stanford_cost"] - 1) * 100,
            "real_growth_pct": (s1["real_stanford_cost"] / s0["real_stanford_cost"] - 1) * 100,
            "cagr_nominal": annualized_growth(s0["stanford_cost"], s1["stanford_cost"], yr),
        }
    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    _ = argparse.ArgumentParser(description=__doc__).parse_args(argv)

    try:
        ensure_dir(config.OUTPUTS_DIR / "tables")
        frames = load_frames()
        peers = frames["peers"]
        universe = frames["universe"]
        aid = frames["aid_curve"]
        trend = frames["trend"]
        roi = frames["roi"]

        results: dict = {
            "meta": {
                "project": config.ARTICLE_TITLE,
                "data": "U.S. Department of Education, College Scorecard",
                "release": "Most Recent Cohorts, June 2026",
                "peer_set": config.PEER_SCHOOLS,
                "seed": config.RANDOM_SEED,
                "cpi_reference_year": config.CPI_REFERENCE_YEAR,
            },
            "focal": focal_summary(peers, universe),
            "rankings": rankings(peers),
            "aid_curve": aid_curve_stats(aid, peers),
            "debt": debt_stats(peers, universe),
            "earnings": earnings_stats(peers, universe),
            "tests": hypothesis_tests(peers, universe),
            "regression": roi_regression(roi),
            "trend": trend_stats(trend),
        }

        dump_json(config.RESULTS_JSON, results)

        # Tidy tables for charts / appendices.
        peers_out = peers[
            [
                "INSTNM",
                "COSTT4_A",
                "NPT4_PRIV",
                "NPT41_PRIV",
                "NPT42_PRIV",
                "NPT43_PRIV",
                "NPT44_PRIV",
                "NPT45_PRIV",
                "MD_EARN_WNE_P10",
                "PCT90_EARN_WNE_P10",
                "PCTPELL",
                "GRAD_DEBT_MDN",
                "C150_4",
                "PAR_ED_PCT_1STGEN",
                "DEP_INC_AVG",
            ]
        ]
        peers_out = peers_out.sort_values("NPT4_PRIV").reset_index(drop=True)
        peers_out.to_csv(config.OUTPUTS_DIR / "tables" / "peer_table.csv", index=False)
        aid.pivot_table(
            index="INSTNM", columns="income_bucket", values="net_price"
        ).reset_index().to_csv(config.OUTPUTS_DIR / "tables" / "aid_curve_table.csv", index=False)
        trend.to_csv(config.OUTPUTS_DIR / "tables" / "trend_table.csv", index=False)

        log.info("analysis complete")
        return 0
    except Exception as exc:  # noqa: BLE001
        log.error("analysis step failed: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
