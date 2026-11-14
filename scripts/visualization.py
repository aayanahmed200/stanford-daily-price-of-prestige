# ==============================================================================
# The Price of Prestige
# Step 5 - publication-quality figures
# ==============================================================================

"""Render every figure used by the article.

House style: Okabe-Ito color-blind-safe palette, DejaVu Sans typography,
300 dpi output, gridlines behind data, and a consistent source note under
each chart (see ``scripts.helpers.save_figure``).

Figures produced
----------------
* ``fig_sticker_cost.png``   -- sticker price, Stanford vs peers
* ``fig_aid_curve.png``      -- net price by family income (the "aid curve")
* ``fig_pell_share.png``     -- share of Pell recipients
* ``fig_debt_by_income.png`` -- median debt by family income group
* ``fig_earnings.png``       -- earnings percentiles 10 years after entry
* ``fig_roi_scatter.png``    -- net price vs median earnings (with OLS line)
* ``fig_cost_trend.png``     -- inflation-adjusted tuition, 2000-2025
* ``interactive_aid_curve.html`` -- hoverable aid curve (Plotly)
"""

from __future__ import annotations

import argparse
import sys

import numpy as np
import pandas as pd

from scripts import config
from scripts.helpers import (
    PALETTE,
    apply_style,
    ensure_dir,
    get_logger,
    save_figure,
)

log = get_logger("visualization")

SOURCE_NOTE = (
    "Source: U.S. Department of Education, College Scorecard "
    "(Most Recent Cohorts, June 2026). Net prices and debts are averages/medians "
    "reported by institutions; see methodology."
)


# ---------------------------------------------------------------------------
# Small plotting helpers
# ---------------------------------------------------------------------------


def _fig(figsize: tuple[float, float] = (10, 6.5)):
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=figsize)
    return fig, ax


def _label_axis(ax, title, xlabel=None, ylabel=None):
    ax.set_title(title, loc="left", pad=14)
    if xlabel:
        ax.set_xlabel(xlabel)
    if ylabel:
        ax.set_ylabel(ylabel)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(PALETTE["faint"])
    ax.spines["bottom"].set_color(PALETTE["faint"])


def _money_ticks(ax, axis="y"):
    from matplotlib.ticker import FuncFormatter

    fmt = FuncFormatter(lambda x, _: f"${x:,.0f}")
    if axis == "y":
        ax.yaxis.set_major_formatter(fmt)
    else:
        ax.xaxis.set_major_formatter(fmt)


def _pct_ticks(ax, axis="y"):
    from matplotlib.ticker import FuncFormatter

    fmt = FuncFormatter(lambda x, _: f"{x * 100:.0f}%")
    if axis == "y":
        ax.yaxis.set_major_formatter(fmt)
    else:
        ax.xaxis.set_major_formatter(fmt)


# ---------------------------------------------------------------------------
# Figure 1 - sticker price
# ---------------------------------------------------------------------------


def fig_sticker_cost(peers: pd.DataFrame, national_median_cost: float) -> str:
    from matplotlib.lines import Line2D

    d = peers.dropna(subset=["COSTT4_A"]).sort_values("COSTT4_A").copy()
    fig, ax = _fig()
    colors = np.where(d["is_stanford"], PALETTE["stanford"], PALETTE["peer"])
    ax.hlines(range(len(d)), 0, d["COSTT4_A"], color=colors, linewidth=4, alpha=0.85)
    ax.scatter(d["COSTT4_A"], range(len(d)), color=colors, s=80, zorder=3)
    ax.scatter(
        d["COSTT4_A"],
        range(len(d)),
        facecolors="white",
        edgecolors=colors,
        s=80,
        zorder=4,
        linewidths=1.2,
    )
    for i, v in enumerate(d["COSTT4_A"]):
        ax.text(v + 900, i, f"${v:,.0f}", va="center", fontsize=9, color=PALETTE["ink"])
    ax.axvline(national_median_cost, color=PALETTE["national"], linestyle="--", linewidth=1.2)
    ax.set_yticks(range(len(d)))
    ax.set_yticklabels(d["INSTNM"].tolist(), fontsize=10)
    ax.set_ylim(-0.7, len(d) - 1 + 1.1)
    ax.set_xlim(0, d["COSTT4_A"].max() * 1.18)
    _money_ticks(ax, axis="x")
    _label_axis(
        ax,
        "The sticker price of an elite education",
        "Total cost of attendance, 2024-25 (tuition + fees + room/board)",
        None,
    )
    # National-median label sits in the clear band above the tallest bar,
    # never on top of a bar (every bar here is well above the national median).
    ax.text(
        national_median_cost,
        len(d) - 1 + 0.75,
        f"U.S. four-year non-profit median: ${national_median_cost:,.0f}",
        fontsize=9,
        ha="center",
        color=PALETTE["slate"],
    )
    legend = [
        Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            markerfacecolor=PALETTE["stanford"],
            markersize=9,
            label="Stanford University",
        ),
        Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            markerfacecolor=PALETTE["peer"],
            markersize=9,
            label="Peer institution",
        ),
    ]
    # Every bar starts at x=0 and runs nearly the full axis width (even the
    # shortest one), so there is no corner of the plot -- left, right, upper,
    # or lower -- that isn't covered by a bar or its end label for at least
    # one row. The only space guaranteed to stay clear of the data is above
    # the axes entirely, next to the title.
    ax.legend(
        handles=legend,
        loc="lower left",
        bbox_to_anchor=(0.0, 1.13, 1.0, 0.1),
        ncol=2,
        mode="expand",
        frameon=False,
    )
    return str(save_figure(fig, "fig_sticker_cost", SOURCE_NOTE))


# ---------------------------------------------------------------------------
# Figure 2 - the aid curve
# ---------------------------------------------------------------------------


def fig_aid_curve(aid: pd.DataFrame) -> str:

    buckets = list(config.INCOME_BUCKETS.values())
    x = np.arange(len(buckets))
    peer = aid[~aid["is_stanford"]]
    stan = aid[aid["is_stanford"]].set_index("income_bucket")["net_price"]

    q25 = peer.groupby("income_bucket")["net_price"].quantile(0.25)
    q75 = peer.groupby("income_bucket")["net_price"].quantile(0.75)
    med = peer.groupby("income_bucket")["net_price"].median()

    fig, ax = _fig()
    ax.fill_between(
        x,
        q25.reindex(buckets).values,
        q75.reindex(buckets).values,
        color=PALETTE["peer_fill"],
        alpha=0.5,
        linewidth=0,
        label="Middle 50% of peer schools",
    )
    ax.plot(
        x,
        med.reindex(buckets).values,
        color=PALETTE["peer"],
        linewidth=2.2,
        marker="o",
        markersize=6,
        label="Peer median",
    )
    stan_vals = [stan.get(b) for b in buckets]
    ax.plot(
        x,
        stan_vals,
        color=PALETTE["stanford"],
        linewidth=3.2,
        marker="o",
        markersize=8,
        label="Stanford University",
    )
    peer_med_vals = med.reindex(buckets).values
    for xi, v, peer_v in zip(x, stan_vals, peer_med_vals, strict=False):
        if v is None or np.isnan(v):
            continue
        # Where the peer median sits close above Stanford's point, an
        # upward label collides with the peer line/marker. Flip the label
        # below the point in that case; otherwise keep it above (default).
        close_above = not np.isnan(peer_v) and 0 <= (peer_v - v) < 4500
        yoffset = -13 if close_above else 9
        va = "top" if close_above else "bottom"
        ax.annotate(
            f"${v:,.0f}",
            (xi, v),
            textcoords="offset points",
            xytext=(0, yoffset),
            ha="center",
            va=va,
            fontsize=9,
            color=PALETTE["stanford"],
            bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.85),
        )
    ax.axhline(0, color=PALETTE["faint"], linewidth=1, linestyle=":")
    ax.set_xticks(x)
    ax.set_xticklabels([b.replace("–", "-") for b in buckets], fontsize=9)
    ax.set_ylim(-6000, 60000)
    _money_ticks(ax)
    _label_axis(
        ax,
        "What Stanford families actually pay, by income",
        "Family income (dependent students)",
        "Average net price per year, 2024-25",
    )
    ax.legend(loc="upper left")
    ax.text(
        0.0,
        -0.32,
        "Negative values mean grants and scholarships exceeded the full cost of attendance.",
        transform=ax.transAxes,
        fontsize=8.5,
        color=PALETTE["slate"],
    )
    return str(save_figure(fig, "fig_aid_curve", SOURCE_NOTE))


# ---------------------------------------------------------------------------
# Figure 3 - Pell share
# ---------------------------------------------------------------------------


def fig_pell_share(peers: pd.DataFrame, national_median_pell: float) -> str:
    from matplotlib.lines import Line2D

    d = peers.dropna(subset=["PCTPELL"]).sort_values("PCTPELL").copy()
    fig, ax = _fig()
    colors = np.where(d["is_stanford"], PALETTE["stanford"], PALETTE["peer"])
    ax.barh(range(len(d)), d["PCTPELL"], color=colors, alpha=0.9, height=0.62)
    for i, v in enumerate(d["PCTPELL"]):
        ax.text(v + 0.004, i, f"{v:.1%}", va="center", fontsize=9, color=PALETTE["ink"])
    ax.axvline(national_median_pell, color=PALETTE["national"], linestyle="--")
    ax.text(
        national_median_pell + 0.004,
        len(d) - 0.8,
        f"National median: {national_median_pell:.1%}",
        fontsize=9,
        color=PALETTE["slate"],
    )
    ax.set_yticks(range(len(d)))
    ax.set_yticklabels(d["INSTNM"].tolist(), fontsize=10)
    # Bound the axis by whichever is larger -- the tallest bar or the
    # national median line -- so the median line/label is never clipped
    # off the right edge of the chart (it used to run past a fixed 0.32).
    ax.set_xlim(0, max(d["PCTPELL"].max(), national_median_pell) * 1.18)
    _pct_ticks(ax, axis="x")
    _label_axis(
        ax,
        "How many students receive Pell Grants?",
        "Share of undergraduate students with Pell Grants",
        None,
    )
    legend = [
        Line2D([0], [0], color=PALETTE["stanford"], lw=5, label="Stanford University"),
        Line2D([0], [0], color=PALETTE["peer"], lw=5, label="Peer"),
    ]
    ax.legend(handles=legend, loc="lower right")
    return str(save_figure(fig, "fig_pell_share", SOURCE_NOTE))


# ---------------------------------------------------------------------------
# Figure 4 - debt by income
# ---------------------------------------------------------------------------


def fig_debt_by_income(peers: pd.DataFrame, national_median_debt: float) -> str:
    """One bar per school (all-graduates median debt), matching the visual
    language of the sticker-cost and Pell-share charts.

    The previous version drew four same-colored sub-bars per school (all
    graduates / low-income / first-gen / high-income) at tiny vertical
    offsets, then stacked four value labels on Stanford's row alone -- since
    the four figures are all close together in dollars, the labels rendered
    on top of each other and were illegible. Peer schools' sub-bars were
    also indistinguishable from one another (same color, position was the
    only cue), so the extra detail wasn't actually readable there either.
    A single bar per school plus one clean breakdown line for Stanford
    keeps every value legible without changing what the chart reports.
    """
    from matplotlib.lines import Line2D

    d = peers.dropna(subset=["GRAD_DEBT_MDN"]).sort_values("GRAD_DEBT_MDN").copy()
    fig, ax = _fig()
    y = np.arange(len(d))
    colors = np.where(d["is_stanford"], PALETTE["stanford"], PALETTE["peer"])
    ax.barh(y, d["GRAD_DEBT_MDN"], color=colors, alpha=0.9, height=0.62)
    for i, v in enumerate(d["GRAD_DEBT_MDN"]):
        ax.text(v + 300, i, f"${v:,.0f}", va="center", fontsize=9, color=PALETTE["ink"])

    ax.axvline(national_median_debt, color=PALETTE["national"], linestyle="--")

    stan = d[d["is_stanford"]].iloc[0]
    breakdown_bits = [
        ("low-income", stan["LO_INC_DEBT_MDN"]),
        ("first-gen", stan["FIRSTGEN_DEBT_MDN"]),
        ("high-income", stan["HI_INC_DEBT_MDN"]),
    ]
    breakdown = " · ".join(
        f"{name} ${v:,.0f}" for name, v in breakdown_bits if not np.isnan(v)
    )

    xmax = (
        max(
            d[["GRAD_DEBT_MDN", "LO_INC_DEBT_MDN", "FIRSTGEN_DEBT_MDN", "HI_INC_DEBT_MDN"]]
            .max()
            .max(),
            national_median_debt,
        )
        * 1.2
    )
    ax.set_xlim(0, xmax)
    ax.set_ylim(-0.7, len(d) - 1 + 1.15)
    ax.text(
        national_median_debt,
        len(d) - 1 + 0.78,
        f"National median: ${national_median_debt:,.0f}",
        fontsize=9,
        ha="center",
        color=PALETTE["slate"],
    )
    ax.set_yticks(y)
    ax.set_yticklabels(d["INSTNM"].tolist(), fontsize=10)
    _money_ticks(ax, axis="x")
    _label_axis(
        ax,
        "The debt that graduates carry",
        "Median cumulative federal debt, all graduates (most recent cohort)",
        None,
    )
    if breakdown:
        # The full breakdown string is wider than any clear strip inside the
        # plot (it would run across several bars no matter where it's
        # anchored), so it goes below the axes as a third footer line --
        # under save_figure()'s source-note and credit lines, not on top of
        # them.
        ax.text(
            0.0,
            -0.27,
            f"Stanford by family background: {breakdown}",
            transform=ax.transAxes,
            ha="left",
            va="top",
            fontsize=8.5,
            color=PALETTE["stanford"],
        )
    legend = [
        Line2D([0], [0], color=PALETTE["stanford"], lw=3, label="Stanford"),
        Line2D([0], [0], color=PALETTE["peer"], lw=3, label="Peer"),
    ]
    ax.legend(handles=legend, loc="lower right", fontsize=9)
    return str(save_figure(fig, "fig_debt_by_income", SOURCE_NOTE))


# ---------------------------------------------------------------------------
# Figure 5 - earnings percentiles
# ---------------------------------------------------------------------------


def fig_earnings(peers: pd.DataFrame, national_median_earn: float) -> str:

    d = peers.dropna(subset=["MD_EARN_WNE_P10"]).sort_values("MD_EARN_WNE_P10").copy()
    fig, ax = _fig()
    y = np.arange(len(d))
    p25 = d["PCT25_EARN_WNE_P10"]
    p75 = d["PCT75_EARN_WNE_P10"]
    med = d["MD_EARN_WNE_P10"]
    p90 = d["PCT90_EARN_WNE_P10"]
    colors = np.where(d["is_stanford"], PALETTE["stanford"], PALETTE["peer"])

    ax.hlines(y, p25, p75, color=colors, linewidth=5, alpha=0.75, label="25th-75th percentile")
    ax.scatter(med, y, color=colors, s=70, zorder=4, label="Median")
    ax.scatter(p90, y, marker="D", color=colors, s=45, zorder=4, label="90th percentile")
    for i, sname in enumerate(d["INSTNM"]):
        if sname == config.FOCAL_SCHOOL:
            ax.annotate(
                f"median ${med.iloc[i]:,.0f}",
                (med.iloc[i], i),
                textcoords="offset points",
                xytext=(-6, 8),
                ha="right",
                fontsize=9,
                color=PALETTE["stanford"],
            )
    ax.axvline(national_median_earn, color=PALETTE["national"], linestyle="--")
    ax.text(
        national_median_earn + 1200,
        len(d) - 0.7,
        f"National median: ${national_median_earn:,.0f}",
        fontsize=9,
        color=PALETTE["slate"],
    )
    ax.set_yticks(y)
    ax.set_yticklabels(d["INSTNM"].tolist(), fontsize=10)
    ax.set_xlim(0, d["PCT90_EARN_WNE_P10"].max() * 1.1)
    _money_ticks(ax, axis="x")
    _label_axis(
        ax,
        "What graduates earn a decade after entering",
        "Annual earnings (median, interquartile range, 90th pctile)",
        None,
    )
    ax.legend(loc="lower right", fontsize=9)
    return str(save_figure(fig, "fig_earnings", SOURCE_NOTE))


# ---------------------------------------------------------------------------
# Figure 6 - ROI scatter
# ---------------------------------------------------------------------------


def fig_roi_scatter(roi: pd.DataFrame, peers: pd.DataFrame) -> str:
    import statsmodels.api as sm

    d = roi.dropna(subset=["NPT4_PRIV", "MD_EARN_WNE_P10", "COUNT_WNE_P10"])
    d = d[d["COUNT_WNE_P10"] >= config.MIN_COUNT_WNE_P10].copy()

    fig, ax = _fig(figsize=(10.5, 6.5))
    ax.scatter(
        d["NPT4_PRIV"],
        d["MD_EARN_WNE_P10"],
        s=18,
        alpha=0.45,
        color=PALETTE["faint"],
        linewidths=0,
        label="Other four-year\nnon-profits",
    )

    peer_ids = set(peers["UNITID"])
    peers_in = d[d["UNITID"].isin(peer_ids)]
    ax.scatter(
        peers_in["NPT4_PRIV"],
        peers_in["MD_EARN_WNE_P10"],
        s=46,
        color=PALETTE["peer"],
        edgecolors="white",
        linewidths=0.7,
        zorder=4,
        label="Peer institution",
    )

    stan = d[d["INSTNM"] == config.FOCAL_SCHOOL]
    ax.scatter(
        stan["NPT4_PRIV"],
        stan["MD_EARN_WNE_P10"],
        marker="*",
        s=420,
        color=PALETTE["stanford"],
        edgecolors="white",
        linewidths=1.0,
        zorder=6,
        label="Stanford University",
    )

    # OLS fit line on the full sample.
    fit = sm.OLS(d["MD_EARN_WNE_P10"], sm.add_constant(d["NPT4_PRIV"])).fit()
    xs = np.linspace(0, d["NPT4_PRIV"].quantile(0.98), 100)
    ax.plot(
        xs,
        fit.params.iloc[0] + fit.params.iloc[1] * xs,
        color=PALETTE["ink"],
        linewidth=1.8,
        linestyle="--",
        alpha=0.8,
        label="Fitted line (all schools)",
    )

    # Annotate Stanford and a few peers.
    labels = [
        config.FOCAL_SCHOOL,
        "Massachusetts Institute of Technology",
        "Princeton University",
        "Harvard University",
        "Rice University",
        "Northwestern University",
    ]
    # Per-school offset overrides where the default (8, 5) crowds a
    # neighboring point -- Rice sits right next to another peer dot above it.
    label_offsets = {"Rice University": (10, -12)}
    for school in labels:
        hit = d[d["INSTNM"] == school]
        if len(hit):
            is_focal = school == config.FOCAL_SCHOOL
            # Stanford's star marker (s=420) is much bigger than peer dots (s=70),
            # so it needs more clearance
            offset = (14, 12) if is_focal else label_offsets.get(school, (8, 5))
            ax.annotate(
                school.replace("University", "U."),
                (hit["NPT4_PRIV"].iloc[0], hit["MD_EARN_WNE_P10"].iloc[0]),
                textcoords="offset points",
                xytext=offset,
                fontsize=8.5,
                color=PALETTE["ink"],
            )

    ax.set_xlim(-2000, 50000)
    ax.set_ylim(0, 175000)
    _money_ticks(ax, "x")
    _money_ticks(ax, "y")
    _label_axis(
        ax,
        "The return on a degree: what students pay vs. what they earn",
        "Average net price per year (2024-25)",
        "Median earnings 10 years after entry",
    )
    ax.legend(loc="upper left", fontsize=9)
    return str(save_figure(fig, "fig_roi_scatter", SOURCE_NOTE))


# ---------------------------------------------------------------------------
# Figure 7 - cost trend
# ---------------------------------------------------------------------------


def fig_cost_trend(trend: pd.DataFrame) -> str:

    t = trend.sort_values("year_int")
    fig, ax = _fig()
    ax.plot(
        t["year_int"],
        t["real_stanford_tuition"],
        color=PALETTE["stanford"],
        linewidth=3.2,
        marker="o",
        markersize=4,
        label="Stanford tuition & fees",
    )
    ax.plot(
        t["year_int"],
        t["real_peer_median_tuition"],
        color=PALETTE["peer"],
        linewidth=2.2,
        label="Peer median",
    )
    ax.plot(
        t["year_int"],
        t["real_national_median_tuition"],
        color=PALETTE["national"],
        linewidth=2.0,
        linestyle="--",
        label="National median (four-year non-profit)",
    )

    start = t["real_stanford_tuition"].iloc[0]
    end = t["real_stanford_tuition"].iloc[-1]
    pct = (end / start - 1) * 100
    ax.annotate(
        f"Real (2025$) tuition at Stanford\n{start:,.0f} → {end:,.0f} ({pct:+.0f}%)",
        xy=(t["year_int"].iloc[-1], end),
        xytext=(-40, 14),
        textcoords="offset points",
        fontsize=9.5,
        color=PALETTE["stanford"],
        ha="right",
        va="bottom",
        arrowprops=dict(arrowstyle="-", color=PALETTE["stanford"], lw=0.8),
    )
    _money_ticks(ax)
    _label_axis(
        ax,
        "Stanford's tuition has kept climbing even after inflation",
        "Academic year",
        "Tuition & required fees (2025 dollars, CPI-adjusted)",
    )
    ax.legend(loc="upper left", fontsize=9)
    return str(save_figure(fig, "fig_cost_trend", SOURCE_NOTE))


# ---------------------------------------------------------------------------
# Interactive figure (Plotly)
# ---------------------------------------------------------------------------


def interactive_aid_curve(aid: pd.DataFrame) -> str:
    import plotly.graph_objects as go

    buckets = list(config.INCOME_BUCKETS.values())
    fig = go.Figure()
    for school, grp in aid.groupby("INSTNM"):
        vals = grp.set_index("income_bucket")["net_price"].reindex(buckets)
        is_stan = school == config.FOCAL_SCHOOL
        fig.add_trace(
            go.Scatter(
                x=buckets,
                y=vals,
                mode="lines+markers",
                name=school,
                line=dict(
                    color="#8C1515" if is_stan else "#3E78B2",
                    width=4 if is_stan else 1.6,
                ),
                opacity=1.0 if is_stan else 0.85,
                hovertemplate="%{x}<br>Net price: $%{y:,.0f}<extra>" + school + "</extra>",
            )
        )
    fig.update_layout(
        title="Average net price by family income — Stanford and its peers",
        xaxis_title="Family income (dependent students)",
        yaxis_title="Average net price per year (2024-25)",
        hovermode="closest",
        template="plotly_white",
        height=600,
        legend=dict(font=dict(size=10)),
        margin=dict(l=60, r=20, t=60, b=60),
    )
    out = config.FIGURES_DIR / "interactive" / "interactive_aid_curve.html"
    ensure_dir(out.parent)
    # full_html=False: emit an embeddable <div>+<script> fragment, not a full
    # standalone document. index.qmd reads this file's raw text and inlines it
    # into the article page with IPython's HTML(); a full_html=True export
    # (its own <html>/<head>/<body> wrapper) gets nested inside the article's
    # own <body>, which is invalid HTML and made the chart render blank/unstable
    # in the published page even though the SVG itself was generated correctly.
    fig.write_html(out, include_plotlyjs="inline", full_html=False)
    log.info("saved interactive figure: %s", out)
    return str(out)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-interactive",
        action="store_true",
        help="skip the Plotly interactive figure (no JS dependency)",
    )
    args = parser.parse_args(argv)

    try:
        apply_style()
        peers = pd.read_csv(config.PROCESSED_PEERS)
        aid = pd.read_csv(config.PROCESSED_DIR / "aid_curve.csv")
        trend = pd.read_csv(config.PROCESSED_TREND)
        roi = pd.read_csv(config.PROCESSED_ROI)
        universe = pd.read_csv(config.PROCESSED_SCORECARD)

        national_median_cost = float(universe["COSTT4_A"].median())
        national_median_pell = float(universe["PCTPELL"].median())
        national_median_debt = float(universe["GRAD_DEBT_MDN"].median())
        national_median_earn = float(universe["MD_EARN_WNE_P10"].median())

        paths = {
            "fig_sticker_cost": fig_sticker_cost(peers, national_median_cost),
            "fig_aid_curve": fig_aid_curve(aid),
            "fig_pell_share": fig_pell_share(peers, national_median_pell),
            "fig_debt_by_income": fig_debt_by_income(peers, national_median_debt),
            "fig_earnings": fig_earnings(peers, national_median_earn),
            "fig_roi_scatter": fig_roi_scatter(roi, peers),
            "fig_cost_trend": fig_cost_trend(trend),
        }
        if not args.skip_interactive:
            paths["interactive_aid_curve"] = interactive_aid_curve(aid)

        log.info("figures complete: %d rendered", len(paths))
        return 0
    except Exception as exc:  # noqa: BLE001
        log.error("visualization step failed: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
