from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import FuncFormatter


# --- style ---
COL_ORANGE = "#F97316"
COL_BLUE_DARK = "#1E3A8A"
COL_GREY = "#6B7280"
COL_GRID = "#E5E7EB"
COL_FRAME = "#D1D5DB"
COL_TEXT = "#374151"
COL_SOURCE = "#000000"
BG_COLOR = "#FFFFFF"


def _apply_axis_style(ax):
    ax.grid(which="major", axis="y", color=COL_GRID, linestyle="--", linewidth=0.5, alpha=0.8)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_linewidth(1.0)
    ax.spines["bottom"].set_linewidth(1.0)
    ax.spines["left"].set_color(COL_FRAME)
    ax.spines["bottom"].set_color(COL_FRAME)
    ax.tick_params(axis="both", which="both", length=4, color=COL_FRAME, labelsize=9, labelcolor=COL_TEXT, direction="out")
    ax.xaxis.label.set_color(COL_TEXT); ax.xaxis.label.set_fontsize(10)
    ax.yaxis.label.set_color(COL_TEXT); ax.yaxis.label.set_fontsize(10)


def _format_quarter_labels(dt_series):
    out = []
    for d in pd.to_datetime(dt_series):
        q_num = ((d.month - 1) // 3) + 1
        out.append(f"{d.year} Q{q_num}")
    return out


def _apply_quarter_ticks(ax, x_dates, max_ticks=12):
    if len(x_dates) <= max_ticks:
        idxs = range(len(x_dates))
    else:
        step = max(1, len(x_dates) // max_ticks)
        idxs = range(0, len(x_dates), step)
    ticks = [x_dates[i] for i in idxs]
    labels = _format_quarter_labels([x_dates[i] for i in idxs])
    ax.set_xticks(ticks)
    ax.set_xticklabels(labels, rotation=0, ha="center", fontsize=9, color=COL_TEXT)


def _draw_title_subtitle(fig, title, subtitle):
    fig.text(0.08, 0.90, title, ha="left", va="bottom", fontsize=14, fontweight="bold", color=COL_TEXT)
    fig.text(0.08, 0.865, subtitle, ha="left", va="bottom", fontsize=10.5, color=COL_TEXT)


def _make_legend_above(ax, fig, ncol=3, handles_labels=None, y_offset=0.04):
    if handles_labels is None:
        handles, labels = ax.get_legend_handles_labels()
    else:
        handles, labels = handles_labels
    leg = fig.legend(handles, labels, loc="upper left", bbox_to_anchor=(0.08, 0.83 - y_offset),
                     frameon=True, ncol=ncol, fontsize=10, handlelength=2.5, columnspacing=1.2, handletextpad=0.6)
    leg.get_frame().set_facecolor(BG_COLOR)
    leg.get_frame().set_edgecolor(COL_FRAME)
    leg.get_frame().set_linewidth(0.8)
    leg.get_frame().set_alpha(0.95)


def _add_wrapped_source(ax, text, y_offset=-0.32, width=120, fontsize=8.5):
    import textwrap
    wrapped = textwrap.fill(text, width=width)
    ax.text(0.0, y_offset, wrapped, transform=ax.transAxes, ha="left", va="top",
            fontsize=fontsize, color=COL_SOURCE, linespacing=1.3)


def _add_author_credit(fig, text="Author: Alborz Moezzi", x=0.98, y=0.06):
    fig.text(x, y, text, ha="right", va="center", fontsize=9.5, color=COL_SOURCE, alpha=0.85)


def figure_migration_inflows(mig_wide: pd.DataFrame, outdir: Path) -> Tuple[Path, Path]:
    fig, ax = plt.subplots(figsize=(12, 7), facecolor=BG_COLOR)
    _apply_axis_style(ax)
    ax.plot(mig_wide["quarter"], mig_wide["immigrants"], color=COL_ORANGE, linewidth=2.0, label="Immigrants (permanent)")
    ax.plot(mig_wide["quarter"], mig_wide["net_non_permanent_residents"], color=COL_BLUE_DARK, linewidth=2.0,
            label="Net non-permanent residents")
    ax.plot(mig_wide["quarter"], mig_wide["total_pressure"], color=COL_GREY, linewidth=2.0,
            label="Total inflow pressure (perm + temp)")
    ax.set_xlabel("Quarter"); ax.set_ylabel("People (count)"); ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f"{int(x):,}"))
    _apply_quarter_ticks(ax, list(mig_wide["quarter"]))
    _draw_title_subtitle(fig, "Population inflow into Alberta remains elevated",
                         "Quarterly arrivals | Permanent residents vs temporary permits")
    _make_legend_above(ax, fig, ncol=3)
    _add_wrapped_source(ax,
        "Note: Net non-permanent residents can be negative when more temporary residents leave than arrive. "
        "Adapted from Statistics Canada Table 17-10-0040-01. This does not constitute an endorsement by Statistics Canada.")
    _add_author_credit(fig)
    outdir.mkdir(parents=True, exist_ok=True)
    p_png = outdir / "figure1_migration_pressure.png"
    p_pdf = outdir / "figure1_migration_pressure.pdf"
    fig.tight_layout(rect=[0.06, 0.10, 1.0, 0.80])
    fig.savefig(p_png, dpi=300, bbox_inches="tight", facecolor=BG_COLOR)
    fig.savefig(p_pdf, dpi=300, bbox_inches="tight", facecolor=BG_COLOR)
    plt.close(fig)
    return p_png, p_pdf


def figure_starts_vs_rate(starts_q: pd.DataFrame, rate_q: pd.DataFrame, outdir: Path) -> Tuple[Path, Path]:
    df = starts_q.merge(rate_q, on="quarter", how="inner").sort_values("quarter")
    fig, axl = plt.subplots(figsize=(12, 7), facecolor=BG_COLOR)
    _apply_axis_style(axl)
    axl.plot(df["quarter"], df["starts_saar_units"], color=COL_ORANGE, linewidth=2.0, label="Housing starts (SAAR, quarterly avg)")
    axl.set_ylabel("Housing starts (SAAR units, Alberta)"); axl.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f"{int(x):,}"))
    _apply_quarter_ticks(axl, list(df["quarter"])); axl.set_xlabel("Quarter")
    axr = axl.twinx()
    axr.plot(df["quarter"], df["policy_rate_pct"], color=COL_BLUE_DARK, linewidth=2.0, label="BoC policy rate (quarter-end)")
    axr.set_ylabel("Policy rate (%)")
    axr.spines["top"].set_visible(False); axr.spines["left"].set_visible(False)
    axr.spines["right"].set_linewidth(1.0); axr.spines["right"].set_color("black")
    axl.spines["left"].set_color("black")
    _draw_title_subtitle(fig, "Builders kept building despite restrictive borrowing costs",
                         "Alberta housing starts vs Bank of Canada policy rate (seasonally adjusted housing starts)")
    handles_l, labels_l = axl.get_legend_handles_labels()
    handles_r, labels_r = axr.get_legend_handles_labels()
    _make_legend_above(axl, fig, ncol=2, handles_labels=(handles_l + handles_r, labels_l + labels_r), y_offset=0.00)
    _add_wrapped_source(axl,
        "Note: Housing starts are SAAR. Policy rate is the BoC target at quarter-end. "
        "Sources: Statistics Canada, Bank of Canada. This does not constitute an endorsement by Statistics Canada.",
        y_offset=-0.36, width=120, fontsize=8.0)
    _add_author_credit(fig)
    outdir.mkdir(parents=True, exist_ok=True)
    p_png = outdir / "figure2_starts_vs_policy_rate.png"
    p_pdf = outdir / "figure2_starts_vs_policy_rate.pdf"
    fig.tight_layout(rect=[0.06, 0.10, 1.0, 0.80])
    fig.savefig(p_png, dpi=300, bbox_inches="tight", facecolor=BG_COLOR)
    fig.savefig(p_pdf, dpi=300, bbox_inches="tight", facecolor=BG_COLOR)
    plt.close(fig)
    return p_png, p_pdf

