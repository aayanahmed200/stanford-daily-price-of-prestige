# ==============================================================================
# The Price of Prestige
# Step 2 - validate raw inputs before any analysis
# ==============================================================================

"""Data-quality checks for the raw inputs.

Checks cover schema, types, duplicate identifiers, unexpected categorical
values, missingness, and basic range sanity. A JSON report is written to
``outputs/validation_report.json`` and the process exits non-zero when any
*hard* check fails (missing columns, duplicate UNITIDs, impossible values).

Soft issues (e.g., high missingness on optional columns) are logged and
recorded but do not fail the run.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import pandas as pd

from scripts import config
from scripts.download import TREND_COLUMNS
from scripts.helpers import get_logger, to_numeric

log = get_logger("validate")

HARD_MISSINGNESS_THRESHOLD = 0.99  # >99% missing on a required column fails


def _load_institution() -> pd.DataFrame:
    """Read the most-recent institution file with the configured columns."""
    if not config.MOST_RECENT_CSV.exists():
        raise FileNotFoundError(
            f"{config.MOST_RECENT_CSV} not found - run `python -m scripts.download` first"
        )
    df = pd.read_csv(
        config.MOST_RECENT_CSV,
        usecols=config.RAW_COLUMNS,
        encoding="utf-8-sig",
        low_memory=False,
    )
    df["INSTNM"] = df["INSTNM"].astype("string").str.strip()
    return df


def validate_institution(df: pd.DataFrame) -> dict:
    """Run all checks on the institution table; return the report fragment."""
    report: dict = {"n_rows": int(len(df)), "n_columns": int(df.shape[1]), "checks": []}

    def check(name: str, passed: bool, detail: str, hard: bool = False) -> None:
        report["checks"].append(
            {"name": name, "passed": bool(passed), "hard": hard, "detail": detail}
        )

    # 1. Required columns present.
    missing_cols = [c for c in config.RAW_COLUMNS if c not in df.columns]
    check(
        "schema: required columns present", not missing_cols, f"missing={missing_cols}", hard=True
    )

    # 2. No duplicate UNITIDs.
    dup = int(df["UNITID"].duplicated().sum())
    check("ids: no duplicate UNITID", dup == 0, f"duplicate rows={dup}", hard=True)

    # 3. Categorical value sanity.
    control_ok = set(df["CONTROL"].dropna()) <= {1, 2, 3}
    check(
        "categorical: CONTROL in {{1,2,3}}",
        control_ok,
        f"values={sorted(df['CONTROL'].dropna().unique())}",
        hard=True,
    )
    highdeg_ok = set(df["HIGHDEG"].dropna()) <= {0, 1, 2, 3, 4}
    check(
        "categorical: HIGHDEG in 0..4",
        highdeg_ok,
        f"values={sorted(df['HIGHDEG'].dropna().unique())}",
        hard=True,
    )

    # 4. Identifier integrity.
    null_ids = int(df["UNITID"].isna().sum())
    check("ids: UNITID non-null", null_ids == 0, f"null ids={null_ids}", hard=True)
    null_names = int(df["INSTNM"].isna().sum())
    check("ids: INSTNM non-null", null_names == 0, f"null names={null_names}", hard=True)

    # 5. Type & range checks on numeric columns.
    for col in config.DOLLAR_COLUMNS | config.INTEGER_COLUMNS:
        num = to_numeric(df[col])
        if col in config.DOLLAR_COLUMNS:
            # Net price by income bracket (NPT41..45_PRIV) may legitimately be
            # negative -- grants exceeding cost isn't unique to the lowest
            # bracket, it just gets rarer as income rises (confirmed in the
            # cleaned data: NPT41/42/43 all have real negative rows; NPT44/45
            # don't, but the same mechanism could produce one). Reject only
            # implausibly large negatives for any bracket column.
            lower = -50000 if col in config.INCOME_BUCKETS else 0
            bad = num[(num < lower)].dropna()
        else:
            bad = num[(num < 0)].dropna()
        check(
            f"range: {col} plausible",
            len(bad) == 0,
            f"implausible={int(len(bad))}",
            hard=(len(bad) > 50),
        )
    for col in config.PERCENT_COLUMNS:
        num = to_numeric(df[col])
        bad = num[(num < 0) | (num > 1)].dropna()
        check(
            f"range: {col} in [0,1]",
            len(bad) == 0,
            f"out-of-range={int(len(bad))}",
            hard=(len(bad) > 10),
        )

    # 6. Missingness per column.
    missing = {col: float(df[col].isna().mean()) for col in df.columns}
    hard_missing = [
        c
        for c in missing
        if missing[c] > HARD_MISSINGNESS_THRESHOLD and c not in ("CCBASIC", "STABBR")
    ]
    check(
        "missingness: required columns populated",
        not hard_missing,
        f">99% missing: {hard_missing}",
        hard=True,
    )
    report["missingness"] = {
        c: round(v, 4) for c, v in sorted(missing.items(), key=lambda kv: -kv[1])
    }

    # 7. Focal school present with the metrics that drive the story.
    focal = df[df["INSTNM"] == config.FOCAL_SCHOOL]
    check("focal: Stanford present", len(focal) == 1, f"matches={int(len(focal))}", hard=True)
    if len(focal):
        r = focal.iloc[0]
        story_cols = [
            "COSTT4_A",
            "NPT4_PRIV",
            "NPT41_PRIV",
            "NPT45_PRIV",
            "MD_EARN_WNE_P10",
            "C150_4",
            "GRAD_DEBT_MDN",
        ]
        missing_story = [c for c in story_cols if pd.isna(r[c])]
        check(
            "focal: story metrics populated",
            not missing_story,
            f"missing={missing_story}",
            hard=True,
        )

    report["hard_failures"] = [c["name"] for c in report["checks"] if c["hard"] and not c["passed"]]
    return report


def validate_trend(path: Path) -> dict:
    """Validate the per-year trend subset."""
    report: dict = {"n_rows": 0, "n_years": 0, "checks": []}
    if not path.exists():
        report["checks"].append(
            {
                "name": "trend file exists",
                "passed": False,
                "hard": True,
                "detail": f"{path.name} missing - run download step",
            }
        )
        report["hard_failures"] = ["trend file exists"]
        return report

    df = pd.read_csv(path, encoding="utf-8-sig")
    report["n_rows"] = int(len(df))
    report["n_years"] = int(df["year"].nunique())
    for col in TREND_COLUMNS:
        if col not in df.columns:
            report["checks"].append(
                {"name": f"trend column {col}", "passed": False, "hard": True, "detail": "missing"}
            )
            report["hard_failures"] = [f"trend column {col}"]
            return report
    report["checks"].append(
        {
            "name": "trend columns present",
            "passed": True,
            "hard": True,
            "detail": str(TREND_COLUMNS),
        }
    )
    report["hard_failures"] = []
    return report


def validate_cpi(path: Path) -> dict:
    """Validate the FRED CPI file has the expected shape."""
    report: dict = {"checks": []}
    if not path.exists():
        report["checks"].append(
            {
                "name": "cpi file exists",
                "passed": False,
                "hard": True,
                "detail": f"{path.name} missing",
            }
        )
        report["hard_failures"] = ["cpi file exists"]
        return report
    with path.open("r", encoding="utf-8") as fh:
        header = next(csv.reader(fh))
    ok = len(header) == 2 and header[0] in ("DATE", "observation_date") and header[1] == "CPIAUCSL"
    report["checks"].append(
        {"name": "cpi schema", "passed": ok, "hard": True, "detail": f"header={header}"}
    )
    report["hard_failures"] = [] if ok else ["cpi schema"]
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    default_report = config.OUTPUTS_DIR / "validation_report.json"
    parser.add_argument("--report", type=Path, default=default_report)
    args = parser.parse_args(argv)

    try:
        df = _load_institution()
        report = {"institution": validate_institution(df)}
        report["trend"] = validate_trend(config.RAW_DIR / "trend_focus.csv")
        report["cpi"] = validate_cpi(config.CPI_CSV)

        from scripts.helpers import dump_json, ensure_dir

        ensure_dir(args.report.parent)
        dump_json(args.report, report)

        failures = []
        for section in ("institution", "trend", "cpi"):
            failures += report[section].get("hard_failures", [])
        if failures:
            log.error("validation FAILED: %s", failures)
            return 1
        log.info(
            "validation passed (%d institutional checks)", len(report["institution"]["checks"])
        )
        return 0
    except Exception as exc:  # noqa: BLE001
        log.error("validation step failed: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
