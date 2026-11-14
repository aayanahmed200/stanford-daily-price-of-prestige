import pandas as pd
from scripts import config
from scripts.preprocess import (
    add_income_bucket_rows,
    build_peer_frame,
    filter_universe,
    real_factor,
)


def _frame() -> pd.DataFrame:
    cols = ["UNITID", "INSTNM", "_key", "HIGHDEG", "CONTROL"]
    rows = [
        (1, "Stanford University", "stanford university", 4, 2),
        (2, "Harvard University", "harvard university", 4, 2),
        (3, "Generic College", "generic college", 4, 2),
        (4, "Community CC", "community cc", 2, 1),
        (5, "For-Profit U", "for-profit u", 4, 3),
    ]
    return pd.DataFrame(rows, columns=cols)


def test_filter_universe_keeps_four_year_nonprofit():
    df = _frame()
    out = filter_universe(df)
    kept = set(out["UNITID"])
    assert kept == {1, 2, 3}
    assert 4 not in kept and 5 not in kept


def test_build_peer_frame_exact_name_match():
    df = _frame()
    peers = build_peer_frame(df)
    assert set(peers["INSTNM"]) == {"Stanford University", "Harvard University"}
    assert peers["is_stanford"].sum() == 1
    assert peers.iloc[0]["INSTNM"] == "Stanford University"


def test_add_income_bucket_rows_melts():
    cols = ["UNITID", "INSTNM", "is_stanford", *config.INCOME_BUCKETS]
    df = pd.DataFrame(
        [
            [1, "Stanford University", True, -2536, -193, 3212, 11092, 53882],
            [2, "Harvard University", False, 8697, 9000, 9500, 10000, 53337],
        ],
        columns=cols,
    )
    out = add_income_bucket_rows(df)
    assert len(out) == 10
    assert set(out["income_bucket"]) == set(config.INCOME_BUCKETS.values())
    stan = out[out["is_stanford"]]
    assert stan.loc[stan["income_bucket"] == "$0\u201330,000", "net_price"].iloc[0] == -2536
    assert out["is_stanford"].dtype == bool


def test_real_factor_uses_reference_year():
    annual = pd.DataFrame({"year": [2020, 2024, 2025], "cpi": [200.0, 250.0, 260.0]})
    factor = real_factor(annual, 2025)
    assert factor.loc[2025] == 1.0
    assert abs(factor.loc[2024] - 260.0 / 250.0) < 1e-9
    assert abs(factor.loc[2020] - 260.0 / 200.0) < 1e-9


def test_real_factor_missing_reference_year_raises():
    annual = pd.DataFrame({"year": [2020], "cpi": [200.0]})
    try:
        real_factor(annual, 2025)
        raised = False
    except Exception:
        raised = True
    assert raised
