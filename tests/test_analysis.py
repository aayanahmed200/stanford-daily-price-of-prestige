import numpy as np
import pandas as pd
from scripts.analysis import debt_stats, earnings_stats, rankings, trend_stats
from scripts.config import FOCAL_SCHOOL


def _peer_frame() -> pd.DataFrame:
    # Stanford ranked: 1st lowest net price, 3rd highest earnings.
    rows = [
        ("Princeton University", 9000, 90000),
        (FOCAL_SCHOOL, 11000, 124000),
        ("Harvard University", 15000, 100000),
        ("Yale University", 17000, 95000),
        ("MIT", 20000, 110000),
    ]
    frame = pd.DataFrame(rows, columns=["INSTNM", "NPT4_PRIV", "MD_EARN_WNE_P10"])
    for col in ["COSTT4_A", "C150_4", "PCTPELL", "GRAD_DEBT_MDN", "PCT90_EARN_WNE_P10"]:
        frame[col] = np.arange(len(frame), dtype=float) + 1
    return frame


def test_rankings_lower_is_better_first():
    peers = _peer_frame()
    out = rankings(peers)
    r = out["NPT4_PRIV"]
    assert r["rank"] == 2
    assert r["n"] == 5
    assert r["best"] == "Princeton University"
    assert r["worst"] == "MIT"


def test_rankings_higher_is_better_first():
    peers = _peer_frame()
    out = rankings(peers)
    r = out["MD_EARN_WNE_P10"]
    assert r["rank"] == 1
    assert r["best"] == FOCAL_SCHOOL


def test_rankings_dropna():
    peers = _peer_frame()
    peers.loc[1, "MD_EARN_WNE_P10"] = np.nan
    out = rankings(peers)
    assert out["MD_EARN_WNE_P10"]["n"] == 4
    assert out["MD_EARN_WNE_P10"]["rank"] is None


def _debt_earnings_peer_frame() -> pd.DataFrame:
    # Stanford is a high outlier on both debt and earnings. If Stanford's own
    # value leaks into "peer_median", the peer median gets pulled toward
    # Stanford instead of describing the other schools.
    rows = [
        (FOCAL_SCHOOL, 100.0, 100.0),
        ("Princeton University", 10.0, 10.0),
        ("Harvard University", 20.0, 20.0),
        ("Yale University", 30.0, 30.0),
        ("MIT", 40.0, 40.0),
    ]
    frame = pd.DataFrame(rows, columns=["INSTNM", "GRAD_DEBT_MDN", "MD_EARN_WNE_P10"])
    for col in ["LO_INC_DEBT_MDN", "HI_INC_DEBT_MDN", "FIRSTGEN_DEBT_MDN"]:
        frame[col] = frame["GRAD_DEBT_MDN"]
    for col in ["PCT25_EARN_WNE_P10", "PCT75_EARN_WNE_P10", "PCT90_EARN_WNE_P10"]:
        frame[col] = frame["MD_EARN_WNE_P10"]
    return frame


def test_debt_stats_peer_median_excludes_stanford():
    peers = _debt_earnings_peer_frame()
    universe = peers.copy()  # national median isn't under test here
    out = debt_stats(peers, universe)
    # Median of the 4 non-Stanford schools (10, 20, 30, 40) is 25, not the
    # all-5-schools median of 30 that including Stanford's 100 would produce.
    assert out["peer_median"]["grad_debt_median"] == 25.0
    assert out["stanford"]["grad_debt_median"] == 100.0


def test_earnings_stats_peer_median_excludes_stanford():
    peers = _debt_earnings_peer_frame()
    universe = peers.copy()
    out = earnings_stats(peers, universe)
    assert out["peer_median"]["median"] == 25.0
    assert out["stanford"]["median"] == 100.0


def test_trend_stats_uses_per_series_windows():
    t = pd.DataFrame(
        {
            "year_int": [1996, 2000, 2005, 2010, 2024],
            "stanford_tuition": [np.nan, 24716, 35000, 45000, 65910],
            "real_stanford_tuition": [np.nan, 46213, 50000, 55000, 67646],
            "peer_median_tuition": [30000, 32000, 40000, 50000, 67250],
            "real_peer_median_tuition": [50000, 55000, 60000, 65000, 69021],
            "national_median_tuition": [1000, 3300, 5000, 7000, 10068],
            "real_national_median_tuition": [2000, 6169, 7000, 8000, 10333],
            "stanford_cost": [np.nan, np.nan, 51760, 70000, 87833],
            "real_stanford_cost": [np.nan, np.nan, 60000, 75000, 90000],
        }
    )
    out = trend_stats(t)
    series = {s["series"]: s for s in out["tuition_series"]}
    assert series["stanford"]["start_year"] == 2000
    assert series["stanford"]["end_year"] == 2024
    assert series["stanford"]["start_nominal"] == 24716
    assert out["stanford_total_cost"]["start_year"] == 2005
    assert out["stanford_total_cost"]["end_year"] == 2024
    assert abs(series["stanford"]["cagr_real"] - ((67646 / 46213) ** (1 / 24) - 1)) < 1e-9
