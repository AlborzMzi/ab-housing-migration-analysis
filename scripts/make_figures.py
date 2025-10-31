"""
Build core figures from processed data.

Usage:
    python scripts/make_figures.py
"""

from pathlib import Path
import pandas as pd

from ab_housing.plotting import figure_migration_inflows, figure_starts_vs_rate

REPO_DIR = Path(__file__).resolve().parents[1]
PROC_DIR = REPO_DIR / "data" / "processed"
FIG_DIR = REPO_DIR / "figures"

def main():
    # Load processed inputs
    mig_wide = pd.read_csv(PROC_DIR / "ab_international_migration_quarterly_wide.csv", parse_dates=["quarter"])
    starts_q = pd.read_csv(PROC_DIR / "ab_housing_starts_quarterly_avg.csv", parse_dates=["quarter"])
    boc_daily = pd.read_csv(PROC_DIR / "boc_policy_rate_daily_clean.csv", parse_dates=["date"])

    # Quarter-end policy rate
    rate_q = (
        boc_daily.set_index("date").resample("Q").last()[["policy_rate_pct"]].reset_index().rename(columns={"date": "quarter"})
    )

    # Figure 1
    figure_migration_inflows(mig_wide, FIG_DIR)

    # Figure 2
    figure_starts_vs_rate(starts_q, rate_q, FIG_DIR)

    print("Figures saved in figures/")

if __name__ == "__main__":
    main()

