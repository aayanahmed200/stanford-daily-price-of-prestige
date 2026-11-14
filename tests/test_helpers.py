import numpy as np
import pandas as pd
import pytest
from scripts.helpers import (
    add_quarter_labels,
    fmt_pct,
    fmt_usd,
    nonmissing_fraction,
    to_numeric,
    uniq_ordered,
)
from scripts.statistics import annualized_growth


def test_to_numeric_maps_suppressed_values():
    s = pd.Series(["123", "NULL", "PrivacySuppressed", "4.5", "", "abc"])
    out = to_numeric(s)
    assert out.iloc[0] == 123
    assert out.iloc[1] is None or np.isnan(out.iloc[1])
    assert np.isnan(out.iloc[2])
    assert out.iloc[3] == 4.5
    assert np.isnan(out.iloc[4])
    assert np.isnan(out.iloc[5])


def test_nonmissing_fraction():
    s = pd.Series([1.0, np.nan, 2.0, np.nan, np.nan])
    assert nonmissing_fraction(s) == 0.4


def test_fmt_usd():
    assert fmt_usd(1235.0) == "$1,235"
    assert fmt_usd(1234.5, ndigits=1) == "$1,234.5"
    assert fmt_usd(None) == "n/a"
    assert fmt_usd(float("nan")) == "n/a"


def test_fmt_pct():
    assert fmt_pct(0.5) == "50.0%"
    assert fmt_pct(0.12345, ndigits=2) == "12.35%"
    assert fmt_pct(None) == "n/a"


def test_annualized_growth():
    assert annualized_growth(100, 121, 2) == pytest.approx(0.1)
    assert np.isnan(annualized_growth(0, 10, 1))
    assert np.isnan(annualized_growth(10, 20, 0))


def test_add_quarter_labels():
    df = pd.DataFrame({"year_int": [2001, 2025]})
    out = add_quarter_labels(df)
    assert out["label"].tolist() == ["2001-02", "2025-26"]


def test_uniq_ordered():
    assert uniq_ordered(["b", "a", "b", "c", "a"]) == ["b", "a", "c"]
