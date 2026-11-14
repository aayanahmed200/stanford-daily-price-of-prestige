# ==============================================================================
# The Price of Prestige
# Step 1 - download raw data from public sources
# ==============================================================================

"""Download the raw inputs for the project.

Fetch, from public sources:

1. The College Scorecard "most recent cohorts" institution file (zip).
2. The full College Scorecard raw-data archive (zip), used for the long-run
   cost trend. Every institution's row is extracted (unfiltered) for each
   configured year file into ``data/raw/trend_focus.csv``; narrowing that
   down to the focal school, its peers, and a national aggregate happens
   later, in ``scripts.preprocess.build_cost_trend``.
3. The CPI-U consumer price index (FRED/St. Louis Fed) for inflation
   adjustment.

The step is idempotent: files that already exist on disk are left untouched
unless ``--force`` is passed.
"""

from __future__ import annotations

import argparse
import csv
import io
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path

from scripts import config
from scripts.helpers import get_logger

log = get_logger("download")

# Columns kept when extracting the long-run trend subset from the raw archive.
TREND_COLUMNS = ["UNITID", "INSTNM", "CONTROL", "COSTT4_A", "TUITIONFEE_IN", "NPT4_PRIV"]


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------


# A browser-like User-Agent: the Scorecard download server and FRED reject the
# default "Python-urllib" agent (HTTP 403) from some hosting ranges.
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


def _download(url: str, dest: Path, *, force: bool = False) -> Path:
    """Download ``url`` to ``dest`` unless it already exists (or --force)."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and not force:
        log.info("exists, skipping: %s", dest.name)
        return dest
    log.info("downloading %s -> %s", url, dest.name)
    tmp = dest.with_suffix(dest.suffix + ".part")
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=300) as resp, tmp.open("wb") as out:
            shutil.copyfileobj(resp, out, length=1024 * 1024)
        tmp.replace(dest)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise
    log.info("downloaded %s (%.1f MB)", dest.name, dest.stat().st_size / 1e6)
    return dest


def _extract_one(zip_path: Path, member: str, dest: Path) -> Path:
    """Extract a single ``member`` of a zip archive to ``dest``."""
    with zipfile.ZipFile(zip_path) as zf:
        with zf.open(member) as src, dest.open("wb") as out:
            shutil.copyfileobj(src, out, length=1024 * 1024)
    return dest


def _read_headers(handle: io.TextIOWrapper) -> tuple[list[str], dict[str, int]]:
    reader = csv.reader(handle)
    columns = next(reader)
    index = {name: i for i, name in enumerate(columns)}
    return columns, index


# ---------------------------------------------------------------------------
# Pipeline steps
# ---------------------------------------------------------------------------


def download_most_recent(force: bool = False) -> Path:
    """Download and extract the most-recent institution file."""
    zip_path = _download(config.MOST_RECENT_ZIP_URL, config.MOST_RECENT_ZIP, force=force)
    if not config.MOST_RECENT_CSV.exists() or force:
        member = "Most-Recent-Cohorts-Institution.csv"
        _extract_one(zip_path, member, config.MOST_RECENT_CSV)
        log.info("extracted %s", config.MOST_RECENT_CSV.name)
    return config.MOST_RECENT_CSV


def download_raw_archive(force: bool = False) -> Path:
    """Download the full historical Scorecard archive (zip only)."""
    return _download(config.RAW_DATA_ZIP_URL, config.RAW_DATA_ZIP, force=force)


def extract_trend_subset(force: bool = False) -> Path:
    """Extract per-institution, per-year trend rows from the raw archive.

    This writes every institution's row (``TREND_COLUMNS`` only) for each
    configured year file to ``data/raw/trend_focus.csv`` -- deliberately
    unfiltered. Splitting those rows into the focal school, peer set, and a
    national aggregate requires knowing ``CONTROL`` and matching names
    against the peer list, which is cheaper to do once downstream (see
    ``scripts.preprocess.build_cost_trend``) than to duplicate here while
    streaming the archive.
    """
    dest = config.RAW_DIR / "trend_focus.csv"
    if dest.exists() and not force:
        log.info("exists, skipping trend extraction: %s", dest.name)
        return dest

    with zipfile.ZipFile(config.RAW_DATA_ZIP) as zf:
        names = {Path(n).name: n for n in zf.namelist() if n.endswith("_PP.csv")}

        with dest.open("w", newline="", encoding="utf-8") as out:
            writer = csv.writer(out)
            writer.writerow(["year", *TREND_COLUMNS])
            for year_file in config.TREND_YEAR_FILES:
                member = names.get(year_file)
                if member is None:
                    log.warning("year file %s not found in archive", year_file)
                    continue
                year = year_file[len("MERGED") : -len("_PP.csv")]
                with zf.open(member) as src:
                    handle = io.TextIOWrapper(src, encoding="utf-8-sig")
                    columns, index = _read_headers(handle)
                    use = [c for c in TREND_COLUMNS if c in index]
                    for row in csv.reader(handle):
                        if len(row) < len(columns):
                            continue
                        values = []
                        for col in use:
                            try:
                                values.append(row[index[col]])
                            except IndexError:
                                values.append("")
                        writer.writerow([year, *values])
                log.info("extracted trend rows: %s", year_file)
    log.info("wrote trend subset: %s", dest)
    return dest


def download_cpi(force: bool = False) -> Path:
    """Download the CPI-U series from FRED."""
    return _download(config.CPI_URL, config.CPI_CSV, force=force)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="re-download everything")
    parser.add_argument(
        "--skip-raw-archive",
        action="store_true",
        help="skip the 470MB historical archive (trend step will fail)",
    )
    args = parser.parse_args(argv)

    try:
        download_most_recent(force=args.force)
        if args.skip_raw_archive:
            log.warning("skipping raw archive download (requested)")
        else:
            download_raw_archive(force=args.force)
            extract_trend_subset(force=args.force)
        download_cpi(force=args.force)
    except Exception as exc:  # noqa: BLE001
        log.error("download step failed: %s", exc)
        return 1
    log.info("download step complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
