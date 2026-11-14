import numpy as np
import pandas as pd
from scripts import config
from scripts.preprocess import clean_institution
from scripts.validate import validate_cpi, validate_institution


def _synthetic_institution(n=50) -> pd.DataFrame:
    rng = np.random.default_rng(0)
    df = pd.DataFrame(index=range(n), columns=config.RAW_COLUMNS, dtype=float)
    df["UNITID"] = np.arange(1000, 1000 + n)
    df["INSTNM"] = [f"University {i}" for i in range(n)]
    df["CONTROL"] = rng.choice([1, 2, 3], n)
    df["HIGHDEG"] = rng.choice([0, 1, 2, 3, 4], n)
    df["STABBR"] = "CA"
    df["CITY"] = [f"City {i}" for i in range(n)]
    df["CCBASIC"] = 1
    for col in config.DOLLAR_COLUMNS:
        df[col] = rng.uniform(0, 50000, n)
    for col in config.PERCENT_COLUMNS:
        df[col] = rng.uniform(0.01, 0.99, n)
    for col in config.INTEGER_COLUMNS - {"UNITID"}:
        df[col] = rng.integers(30, 5000, n)
    df["SAT_AVG"] = rng.uniform(800, 1600, n)
    df["UNITID"] = np.arange(1000, 1000 + n)
    df.loc[df["INSTNM"] == "University 0", "INSTNM"] = config.FOCAL_SCHOOL
    # Give Stanford valid story metrics.
    for col in [
        "COSTT4_A",
        "NPT4_PRIV",
        "NPT41_PRIV",
        "NPT45_PRIV",
        "MD_EARN_WNE_P10",
        "C150_4",
        "GRAD_DEBT_MDN",
    ]:
        df.loc[df["INSTNM"] == config.FOCAL_SCHOOL, col] = rng.uniform(0, 50000)
    return df


def test_validate_institution_passes_clean_frame():
    report = validate_institution(_synthetic_institution())
    assert report["hard_failures"] == []
    assert report["n_rows"] == 50
    assert report["checks"]


def test_validate_institution_catches_duplicate_ids():
    df = _synthetic_institution()
    df.loc[1, "UNITID"] = df.loc[0, "UNITID"]
    report = validate_institution(df)
    assert any("duplicate" in c["name"] and not c["passed"] for c in report["checks"])


def test_validate_institution_catches_bad_control():
    df = _synthetic_institution()
    df.loc[2, "CONTROL"] = 99
    report = validate_institution(df)
    assert any("CONTROL" in c["name"] and not c["passed"] for c in report["checks"])


def test_validate_institution_negative_low_income_net_price_is_ok():
    df = _synthetic_institution()
    df["NPT41_PRIV"] = -2500  # aid exceeding cost is legitimate
    report = validate_institution(df)
    assert report["hard_failures"] == []


def test_validate_institution_negative_net_price_ok_for_every_income_bracket():
    """The same "aid can exceed cost" logic applies to all five income
    brackets (NPT41-45), not just the lowest one -- the real cleaned data has
    genuine small negative values in NPT42 and NPT43 too, so a floor that
    only special-cases NPT41 flags legitimate data as implausible (a soft
    failure below the hard-failure row-count threshold, so it wouldn't show
    up in hard_failures -- check the specific range check instead)."""
    for col in ["NPT41_PRIV", "NPT42_PRIV", "NPT43_PRIV", "NPT44_PRIV", "NPT45_PRIV"]:
        df = _synthetic_institution()
        df[col] = -2500
        report = validate_institution(df)
        range_check = next(c for c in report["checks"] if c["name"] == f"range: {col} plausible")
        assert range_check["passed"], f"{col} should tolerate a small negative value"


def test_validate_cpi_accepts_observation_date_header(tmp_path):
    p = tmp_path / "cpi.csv"
    p.write_text("observation_date,CPIAUCSL\n2025-01-01,320.0\n", encoding="utf-8")
    report = validate_cpi(p)
    assert report["hard_failures"] == []


def test_validate_cpi_rejects_bad_header(tmp_path):
    p = tmp_path / "cpi.csv"
    p.write_text("foo,bar\n1,2\n", encoding="utf-8")
    report = validate_cpi(p)
    assert "cpi schema" in report["hard_failures"]


def test_clean_institution_removes_suppressed(tmp_path, monkeypatch):
    raw = tmp_path / "inst.csv"
    cols = config.RAW_COLUMNS
    header = ",".join(cols)
    row = {c: "1" if c == "UNITID" else "" for c in cols}
    row["INSTNM"] = " Some University "
    row["NPT4_PRIV"] = "PrivacySuppressed"
    row["C150_4"] = "0.9"
    raw.write_text(header + "\n" + ",".join(row[c] for c in cols) + "\n", encoding="utf-8")
    monkeypatch.setattr(config, "MOST_RECENT_CSV", raw)
    out = clean_institution()
    assert out["INSTNM"].iloc[0] == "Some University"
    assert np.isnan(out["NPT4_PRIV"].iloc[0])
    assert out["C150_4"].iloc[0] == 0.9
