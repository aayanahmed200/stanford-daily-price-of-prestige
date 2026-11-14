# ==============================================================================
# The Price of Prestige
# Shared helpers: logging, I/O, data cleaning utilities, chart style.
# ==============================================================================

"""Small, dependency-light helpers shared across the pipeline.

The module intentionally contains no analytics logic; it exists so that the
pipeline steps (download, validate, preprocess, analyze, visualize) stay
focused and readable.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from scripts.config import FIGURES_DIR, OUTPUTS_DIR, PROJECT_ROOT

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_LOGGERS: set[str] = set()


def get_logger(name: str) -> logging.Logger:
    """Return a configured logger for ``name`` (configured once per name)."""
    if name in _LOGGERS:
        return logging.getLogger(name)
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(_LOG_FORMAT))
        logger.addHandler(handler)
    _LOGGERS.add(name)
    return logger


# ---------------------------------------------------------------------------
# Paths / I/O
# ---------------------------------------------------------------------------


def ensure_dir(path: Path) -> Path:
    """Create ``path`` (and parents) if missing; return the path."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def dump_json(path: Path, payload: Any) -> None:
    """Serialize ``payload`` to JSON with human-friendly formatting."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, sort_keys=False, default=_json_default)
    get_logger("helpers").info("wrote %s", path)


def load_json(path: Path) -> Any:
    """Load a JSON file written by :func:`dump_json`."""
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _json_default(obj: Any) -> Any:
    """Serialize numpy scalars and pandas values into plain JSON types."""
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, (pd.Timestamp,)):
        return obj.isoformat()
    if isinstance(obj, float) and np.isnan(obj):  # pragma: no cover
        return None
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


# ---------------------------------------------------------------------------
# Data cleaning
# ---------------------------------------------------------------------------

SUPPRESSED_VALUES = {"NULL", "PrivacySuppressed", "", "None"}


def to_numeric(series: pd.Series) -> pd.Series:
    """Coerce a Scorecard series to numeric, mapping suppressed markers to NaN.

    The raw Scorecard CSVs use the strings ``NULL`` and ``PrivacySuppressed``
    to encode missing and suppressed values.
    """
    return pd.to_numeric(series.replace(SUPPRESSED_VALUES, np.nan), errors="coerce")


def nonmissing_fraction(series: pd.Series) -> float:
    """Share of non-null observations in ``series`` (float in 0..1)."""
    return float(series.notna().mean())


# ---------------------------------------------------------------------------
# Number formatting
# ---------------------------------------------------------------------------


def fmt_usd(value: float | int | None, ndigits: int = 0) -> str:
    """Format ``value`` as a U.S. dollar amount (or ``"n/a"``)."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "n/a"
    return f"${value:,.{ndigits}f}"


def fmt_pct(value: float | None, ndigits: int = 1) -> str:
    """Format a proportion (0..1) as a percentage string."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "n/a"
    return f"{value * 100:.{ndigits}f}%"


def fmt_sig(value: float | None, ndigits: int = 3) -> str:
    """Format a test statistic or p-value with ``ndigits`` decimals."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "n/a"
    return f"{value:.{ndigits}f}"


# ---------------------------------------------------------------------------
# Chart style (publication house style)
# ---------------------------------------------------------------------------

# Accessible, color-blind-safe palette (Okabe-Ito).
PALETTE = {
    "stanford": "#8C1515",  # Stanford cardinal red
    "ink": "#1F2933",
    "faint": "#B4BCC4",
    "grid": "#E1E6EA",
    "paper": "#FFFFFF",
    "slate": "#5B6770",
    "peer": "#3E78B2",
    "peer_fill": "#BFD7EA",
    "national": "#757575",
    "focus": "#C1121F",
    "good": "#2E7D32",
    "bad": "#C1121F",
    "accent": "#E69F00",
}

# Matplotlib rcParams overrides implementing the house style.
MATPLOTLIB_RCPARAMS = {
    "figure.figsize": (9.0, 5.5),
    "figure.dpi": 150,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "font.family": "DejaVu Sans",
    "font.size": 11,
    "axes.titlesize": 14,
    "axes.titleweight": "bold",
    "axes.titlecolor": PALETTE["ink"],
    "axes.labelsize": 11.5,
    "axes.labelcolor": PALETTE["ink"],
    "axes.edgecolor": PALETTE["grid"],
    "axes.linewidth": 0.8,
    "axes.grid": True,
    "axes.axisbelow": True,
    "grid.color": PALETTE["grid"],
    "grid.linewidth": 0.7,
    "xtick.color": PALETTE["ink"],
    "ytick.color": PALETTE["ink"],
    "xtick.labelsize": 10.5,
    "ytick.labelsize": 10.5,
    "legend.frameon": False,
    "figure.facecolor": PALETTE["paper"],
    "axes.facecolor": PALETTE["paper"],
    "text.color": PALETTE["ink"],
}


def apply_style() -> None:
    """Apply the house matplotlib style and register figure directories."""
    import matplotlib as mpl
    from matplotlib import pyplot as plt

    mpl.rcParams.update(MATPLOTLIB_RCPARAMS)
    ensure_dir(FIGURES_DIR)
    ensure_dir(OUTPUTS_DIR)
    plt.close("all")


def save_figure(fig: Any, name: str, subtitle: str | None = None) -> Path:
    """Save ``fig`` to ``figures/<name>.png`` at 300 dpi and return its path.

    A small source line (and masthead credit) is drawn under the axes when
    ``subtitle`` is given.
    """
    import matplotlib.pyplot as plt

    path = FIGURES_DIR / f"{name}.png"
    if subtitle:
        fig.text(
            0.0,
            -0.14,
            subtitle,
            ha="left",
            va="top",
            fontsize=8.5,
            color=PALETTE["slate"],
            transform=fig.axes[0].transAxes,
        )
        fig.text(
            0.0,
            -0.205,
            "The Stanford Daily",
            ha="left",
            va="top",
            fontsize=8.5,
            style="italic",
            color=PALETTE["slate"],
            transform=fig.axes[0].transAxes,
        )
    fig.savefig(path, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    get_logger("helpers").info("saved figure: %s", path)
    return path


# ---------------------------------------------------------------------------
# Misc
# ---------------------------------------------------------------------------


def add_quarter_labels(
    df: pd.DataFrame, year_col: str = "year_int", out_col: str = "label"
) -> pd.DataFrame:
    """Convert academic-year ints (2001 -> 2001-02) into short labels."""
    out = df.copy()
    out[out_col] = out[year_col].astype(str) + "-" + (out[year_col] + 1).astype(str).str[-2:]
    return out


def uniq_ordered(values: Iterable[Any]) -> list[Any]:
    """Return unique values preserving first-seen order."""
    return list(dict.fromkeys(values))


def pretty_table(df: pd.DataFrame, n: int = 40) -> str:
    """Render a pandas DataFrame for logs with sane width settings."""
    with pd.option_context("display.max_rows", n, "display.width", 160):
        return df.to_string(index=False)


def drop_missing(df: pd.DataFrame, columns: Iterable[str]) -> pd.DataFrame:
    """Drop rows missing any of ``columns`` (silently)."""
    cols = list(columns)
    return df.dropna(subset=cols).copy()


def signif(x: float | None, digits: int = 3) -> str:
    """Format ``x`` with ``digits`` significant decimals, else 'n/a'."""
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "n/a"
    return f"{x:.{digits}f}"


def relpath_for_article(path: Path) -> str:
    """Return ``path`` relative to the repo root for README/article links."""
    return path.relative_to(PROJECT_ROOT).as_posix()
