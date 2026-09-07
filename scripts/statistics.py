# ==============================================================================
# The Price of Prestige
# Statistical toolkit
# ==============================================================================

"""Statistical functions used by the analysis.

Every routine returns plain Python dicts (JSON-serializable) so the results
can be persisted to ``outputs/results.json`` and quoted directly in the
article. Bootstrap methods are seeded for full reproducibility.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

from scripts.config import RANDOM_SEED


def bootstrap_median_ci(
    data: pd.Series,
    n_boot: int = 10000,
    ci_level: float = 0.95,
    seed: int = RANDOM_SEED,
) -> dict[str, float]:
    """Bootstrap confidence interval for a population median.

    Returns ``{"median", "ci_low", "ci_high", "n", "n_boot"}``.
    """
    values = np.asarray(data.dropna(), dtype=float)
    if len(values) == 0:
        raise ValueError("bootstrap_median_ci: empty input")
    rng = np.random.default_rng(seed)
    medians = np.empty(n_boot)
    for i in range(n_boot):
        sample = rng.choice(values, size=len(values), replace=True)
        medians[i] = np.median(sample)
    alpha = (1 - ci_level) / 2
    lo, hi = np.quantile(medians, [alpha, 1 - alpha])
    return {
        "median": float(np.median(values)),
        "ci_low": float(lo),
        "ci_high": float(hi),
        "n": int(len(values)),
        "n_boot": n_boot,
    }


def bootstrap_ratio_ci(
    numerator: pd.Series,
    denominator: pd.Series,
    n_boot: int = 10000,
    ci_level: float = 0.95,
    seed: int = RANDOM_SEED,
) -> dict[str, float]:
    """Bootstrap CI for the median of ``numerator/denominator``."""
    a = np.asarray(numerator, dtype=float)
    b = np.asarray(denominator, dtype=float)
    mask = np.isfinite(a) & np.isfinite(b) & (b > 0)
    a, b = a[mask], b[mask]
    ratio = a / b
    return bootstrap_median_ci(pd.Series(ratio), n_boot=n_boot, ci_level=ci_level, seed=seed)


def mann_whitney(x: pd.Series, y: pd.Series) -> dict[str, Any]:
    """Two-sided Mann-Whitney U test with a Hodges-Lehmann style effect size.

    Returns ``{"u", "p_value", "n1", "n2", "median_diff", "interpretation"}``.
    """
    a = np.asarray(x.dropna(), dtype=float)
    b = np.asarray(y.dropna(), dtype=float)
    stat, p = stats.mannwhitneyu(a, b, alternative="two-sided")
    median_diff = float(np.median(a) - np.median(b))
    return {
        "u": float(stat),
        "p_value": float(p),
        "n1": int(len(a)),
        "n2": int(len(b)),
        "median_diff": median_diff,
        "interpretation": _interpret_p(p),
    }


def cohens_d(x: pd.Series, y: pd.Series) -> dict[str, float]:
    """Cohen's d (pooled standard deviation) effect size.

    When one group has a single observation (e.g., comparing one school to a
    group), the single-observation group's variance is undefined and the
    other group's standard deviation is used as the reference.
    """
    a = np.asarray(x.dropna(), dtype=float)
    b = np.asarray(y.dropna(), dtype=float)
    n1, n2 = len(a), len(b)
    if n1 == 0 or n2 == 0:
        return {"cohens_d": float("nan"), "n1": n1, "n2": n2, "pooled_sd": float("nan")}
    s1 = a.var(ddof=1) if n1 > 1 else float("nan")
    s2 = b.var(ddof=1) if n2 > 1 else float("nan")
    if n1 > 1 and n2 > 1:
        pooled = np.sqrt(((n1 - 1) * s1 + (n2 - 1) * s2) / (n1 + n2 - 2))
    else:
        pooled = (
            np.sqrt(s2) if np.isfinite(s2) else np.sqrt(s1) if np.isfinite(s1) else float("nan")
        )
    d = (a.mean() - b.mean()) / pooled if np.isfinite(pooled) and pooled > 0 else float("nan")
    return {"cohens_d": float(d), "n1": n1, "n2": n2, "pooled_sd": float(pooled)}


def pearson_with_ci(x: pd.Series, y: pd.Series, seed: int = RANDOM_SEED) -> dict[str, float]:
    """Pearson r with a bootstrap CI."""
    frame = pd.DataFrame({"x": x, "y": y}).dropna()
    r = stats.pearsonr(frame["x"], frame["y"])[0]
    rng = np.random.default_rng(seed)
    boot = np.empty(2000)
    for i in range(2000):
        idx = rng.integers(0, len(frame), size=len(frame))
        boot[i] = stats.pearsonr(frame["x"].iloc[idx], frame["y"].iloc[idx])[0]
    lo, hi = np.quantile(boot, [0.025, 0.975])
    return {"r": float(r), "ci_low": float(lo), "ci_high": float(hi), "n": int(len(frame))}


def ols_robust(
    df: pd.DataFrame,
    outcome: str,
    predictors: list[str],
) -> dict[str, Any]:
    """Ordinary least squares with HC3 robust standard errors.

    Returns the model summary as a JSON-friendly dict. All predictors are
    standardized internally, so coefficients are comparable "per 1 SD"
    effects.
    """
    import statsmodels.api as sm
    from statsmodels.stats.outliers_influence import variance_inflation_factor

    d = df[[outcome, *predictors]].dropna().copy()
    if len(d) < len(predictors) + 10:
        raise ValueError("ols_robust: too few observations")
    y = np.asarray(d[outcome], dtype=float)
    X_raw = d[predictors].astype(float)
    X = (X_raw - X_raw.mean()) / X_raw.std(ddof=0)
    design = sm.add_constant(X)
    model = sm.OLS(y, design).fit(cov_type="HC3")

    terms = []
    conf = model.conf_int()
    for i, name in enumerate(["intercept", *predictors]):
        terms.append(
            {
                "name": name,
                "coef": float(model.params.iloc[i]),
                "se": float(model.bse.iloc[i]),
                "ci_low": float(conf.iloc[i, 0]),
                "ci_high": float(conf.iloc[i, 1]),
                "p_value": float(model.pvalues.iloc[i]),
            }
        )

    try:
        vifs = {
            name: float(variance_inflation_factor(np.column_stack([np.ones(len(X)), X]), j + 1))
            for j, name in enumerate(predictors)
        }
    except Exception:  # noqa: BLE001
        vifs = {}

    return {
        "outcome": outcome,
        "predictors": predictors,
        "n": int(model.nobs),
        "r_squared": float(model.rsquared),
        "adj_r_squared": float(model.rsquared_adj),
        "f_p_value": float(model.f_pvalue),
        "terms": terms,
        "vif": vifs,
        "focal_residual": None,
    }


def add_focal_residual(
    model: dict[str, Any],
    df: pd.DataFrame,
    outcome: str,
    predictors: list[str],
    focal: str = "Stanford University",
    log_outcome: bool = False,
) -> dict[str, Any]:
    """Attach the out-of-model residual for the focal school.

    ``df`` must contain ``UNITID`` plus the model variables; the focal school
    is identified by exact ``INSTNM`` match.

    ``residual_pct`` expresses the residual as a percent of the fitted value.
    When ``outcome`` is on a natural (dollar-like) scale, that is simply
    ``(actual - fitted) / fitted * 100``. When ``log_outcome=True`` (``outcome``
    is a log-transformed variable, e.g. ``log(earnings)``), ``actual`` and
    ``fitted`` are both in log units, so the percent difference on the
    original scale is instead ``(exp(actual - fitted) - 1) * 100`` -- the
    plain-scale formula applied to log values would silently compute a
    meaningless number. ``actual_dollars``/``fitted_dollars`` (the
    back-transformed, natural-scale values) are also attached in that case.
    """
    import statsmodels.api as sm

    d = df[["UNITID", outcome, *predictors]].dropna().copy()
    y = np.asarray(d[outcome], dtype=float)
    X_raw = d[predictors].astype(float)
    X = (X_raw - X_raw.mean()) / X_raw.std(ddof=0)
    design = sm.add_constant(X)
    fit = sm.OLS(y, design).fit(cov_type="HC3")

    focal_ids = set(df.loc[df["INSTNM"] == focal, "UNITID"])
    mask = d["UNITID"].isin(focal_ids).to_numpy()
    if not mask.any():
        return model
    fitted = float(np.asarray(fit.predict(design))[mask][0])
    actual = float(y[mask][0])
    residual = actual - fitted
    model["focal_residual"] = {
        "school": focal,
        "actual": actual,
        "fitted": fitted,
        "residual": residual,
        "residual_pct": ((np.exp(residual) - 1) if log_outcome else (residual / fitted)) * 100,
    }
    if log_outcome:
        model["focal_residual"]["actual_dollars"] = float(np.exp(actual))
        model["focal_residual"]["fitted_dollars"] = float(np.exp(fitted))
    return model


def annualized_growth(start: float, end: float, years: float) -> float:
    """Compound annual growth rate (CAGR) as a fraction."""
    if start <= 0 or end <= 0 or years <= 0:
        return float("nan")
    return (end / start) ** (1 / years) - 1


def _interpret_p(p: float) -> str:
    if p < 0.001:
        return "significant at p<0.001"
    if p < 0.05:
        return "significant at p<0.05"
    if p < 0.1:
        return "marginal (p<0.1)"
    return "not statistically significant"


__all__ = [
    "bootstrap_median_ci",
    "bootstrap_ratio_ci",
    "mann_whitney",
    "cohens_d",
    "pearson_with_ci",
    "ols_robust",
    "add_focal_residual",
    "annualized_growth",
]
