import numpy as np
import pandas as pd
import pytest
from scripts.config import RANDOM_SEED
from scripts.statistics import (
    add_focal_residual,
    bootstrap_median_ci,
    cohens_d,
    mann_whitney,
    ols_robust,
    pearson_with_ci,
)


def test_bootstrap_median_ci_recovers_median():
    rng = np.random.default_rng(0)
    data = pd.Series(rng.normal(1000, 100, size=500))
    out = bootstrap_median_ci(data, n_boot=500, seed=RANDOM_SEED)
    assert out["n"] == 500
    assert abs(out["median"] - 1000) < 30
    assert out["ci_low"] < out["median"] < out["ci_high"]
    assert out["median"] == pytest.approx(float(data.median()))


def test_bootstrap_median_ci_is_seeded():
    data = pd.Series(np.arange(1, 101, dtype=float))
    a = bootstrap_median_ci(data, n_boot=200, seed=42)
    b = bootstrap_median_ci(data, n_boot=200, seed=42)
    assert a == b


def test_bootstrap_median_ci_rejects_empty():
    with pytest.raises(ValueError):
        bootstrap_median_ci(pd.Series([np.nan]))


def test_mann_whitney_separates_distributions():
    a = pd.Series(np.random.default_rng(1).normal(0, 1, 100))
    b = pd.Series(np.random.default_rng(1).normal(5, 1, 100))
    out = mann_whitney(a, b)
    assert out["p_value"] < 0.001
    assert out["n1"] == 100 and out["n2"] == 100


def test_cohens_d_single_observation_group():
    one = pd.Series([10.0])
    many = pd.Series(np.arange(1, 21, dtype=float))
    out = cohens_d(one, many)
    assert np.isfinite(out["cohens_d"])
    assert out["n1"] == 1 and out["n2"] == 20


def test_pearson_with_ci_perfect_correlation():
    x = pd.Series(np.arange(50.0))
    out = pearson_with_ci(x, x)
    assert abs(out["r"] - 1.0) < 1e-9
    assert out["n"] == 50


def test_ols_robust_on_synthetic():
    rng = np.random.default_rng(7)
    n = 200
    x1 = rng.normal(size=n)
    x2 = rng.normal(size=n)
    y = 2.0 + 1.5 * x1 + 0.5 * x2 + rng.normal(scale=0.5, size=n)
    df = pd.DataFrame({"y": y, "x1": x1, "x2": x2})
    model = ols_robust(df, "y", ["x1", "x2"])
    terms = {t["name"]: t for t in model["terms"]}
    assert abs(terms["x1"]["coef"] - 1.5) < 0.2
    assert abs(terms["x2"]["coef"] - 0.5) < 0.2
    assert model["n"] == n
    assert model["r_squared"] > 0.5


def test_add_focal_residual_outlier():
    rng = np.random.default_rng(3)
    n = 150
    x = rng.normal(size=n)
    y = 1.0 + 2.0 * x + rng.normal(scale=0.5, size=n)
    df = pd.DataFrame({"UNITID": np.arange(n), "INSTNM": ["Other"] * n, "y": y, "x": x})
    df.loc[0, "INSTNM"] = "Stanford University"
    df.loc[0, "y"] = df.loc[0, "y"] + 3.0
    model = add_focal_residual({"terms": []}, df, "y", ["x"])
    assert model["focal_residual"]["actual"] > model["focal_residual"]["fitted"]
    assert model["focal_residual"]["residual"] > 2.0
    # Plain (non-log) outcome: residual_pct is (actual-fitted)/fitted*100.
    res = model["focal_residual"]
    expected_pct = (res["actual"] - res["fitted"]) / res["fitted"] * 100
    assert res["residual_pct"] == pytest.approx(expected_pct)
    assert "actual_dollars" not in res


def test_add_focal_residual_log_outcome_uses_exp_transform():
    """When the outcome is log-scale, residual_pct must use the exp-based
    formula, not the plain (actual-fitted)/fitted formula -- applying the
    plain formula to log-scale values produces a nonsensical percentage
    (log-dollar values are ~O(10), so dividing by one gives absurd swings)."""
    rng = np.random.default_rng(5)
    n = 150
    x = rng.normal(size=n)
    log_y = 11.0 + 0.3 * x + rng.normal(scale=0.05, size=n)
    df = pd.DataFrame({"UNITID": np.arange(n), "INSTNM": ["Other"] * n, "log_y": log_y, "x": x})
    df.loc[0, "INSTNM"] = "Stanford University"
    # Nudge Stanford's log-outcome up by a known amount so the expected
    # percent uplift is easy to check independently.
    df.loc[0, "log_y"] = df.loc[0, "log_y"] + np.log(1.5)  # ~50% above its fitted value

    plain_model = add_focal_residual({"terms": []}, df, "log_y", ["x"], log_outcome=False)
    log_model = add_focal_residual({"terms": []}, df, "log_y", ["x"], log_outcome=True)

    plain_res = plain_model["focal_residual"]
    log_res = log_model["focal_residual"]
    # Same underlying fit -> same residual in log units either way.
    assert log_res["residual"] == pytest.approx(plain_res["residual"])
    # But residual_pct must differ: the log-aware version follows exp(residual)-1,
    # not the plain-scale (actual-fitted)/fitted ratio.
    expected_log_pct = (np.exp(log_res["residual"]) - 1) * 100
    assert log_res["residual_pct"] == pytest.approx(expected_log_pct)
    assert log_res["residual_pct"] != pytest.approx(plain_res["residual_pct"])
    # Back-transformed dollar fields are attached only for the log case.
    assert log_res["actual_dollars"] == pytest.approx(np.exp(log_res["actual"]))
    assert log_res["fitted_dollars"] == pytest.approx(np.exp(log_res["fitted"]))
    assert "actual_dollars" not in plain_res


def test_ols_robust_too_few_rows():
    df = pd.DataFrame({"y": [1, 2, 3], "x1": [1, 2, 3]})
    with pytest.raises(ValueError):
        ols_robust(df, "y", ["x1"])
