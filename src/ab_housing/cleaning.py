from __future__ import annotations

from pathlib import Path
from typing import Tuple

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------
# Helper: project directories (resolved from this file location)
# ---------------------------------------------------------------------
REPO_DIR = Path(__file__).resolve().parents[2]  # .../ab-housing-migration-analysis
DATA_DIR = REPO_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROC_DIR = DATA_DIR / "processed"
PROC_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------
# 1. Bank of Canada policy rate
# ---------------------------------------------------------------------
def clean_boc_policy_rate(file_path: Path) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Clean the daily policy rate series and derive month-end levels and change dates.

    Parameters
    ----------
    file_path : Path
        CSV with columns: Date, V39079 (target rate). Non-numeric rows may appear.

    Returns
    -------
    boc_daily : DataFrame
        Clean daily step series with columns: ['date','policy_rate_pct'].
    boc_monthly_end : DataFrame
        Month-end levels without averaging; last observation in each month.
    boc_changes : DataFrame
        Rows where the policy rate changes (announcement dates).
    """
    df = pd.read_csv(file_path)
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
    df = df.rename(columns={"v39079": "policy_rate_pct"})

    # Keep rows with numeric rate
    df = df[df["policy_rate_pct"].apply(lambda x: str(x).replace(".", "", 1).isdigit())].copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["policy_rate_pct"] = pd.to_numeric(df["policy_rate_pct"], errors="coerce")
    df = df.dropna(subset=["date", "policy_rate_pct"]).sort_values("date").reset_index(drop=True)

    boc_daily = df.copy()
    boc_monthly_end = boc_daily.set_index("date").resample("M").last().reset_index()
    boc_changes = (
        boc_daily.loc[boc_daily["policy_rate_pct"].shift(1) != boc_daily["policy_rate_pct"],
                      ["date", "policy_rate_pct"]]
        .reset_index(drop=True)
    )

    boc_daily.to_csv(PROC_DIR / "boc_policy_rate_daily_clean.csv", index=False)
    boc_monthly_end.to_csv(PROC_DIR / "boc_policy_rate_monthly_end.csv", index=False)
    boc_changes.to_csv(PROC_DIR / "boc_policy_rate_change_dates.csv", index=False)
    return boc_daily, boc_monthly_end, boc_changes


# ---------------------------------------------------------------------
# 2. Alberta housing starts (SAAR)
# ---------------------------------------------------------------------
def clean_housing_starts(file_path: Path) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Transform a wide monthly SAAR file (row='Alberta') into monthly & quarterly tables.

    Parameters
    ----------
    file_path : Path
        CSV where one row is 'Alberta' and columns are 'Jan-00','Feb-00',...

    Returns
    -------
    starts_monthly : DataFrame [date, starts_saar_units]
    starts_quarterly : DataFrame [quarter, starts_saar_units] quarterly mean of SAAR
    """
    raw = pd.read_csv(file_path)
    raw.columns = raw.columns.astype(str)

    ab_row = raw[raw["Geography"].str.strip().str.lower() == "alberta"]
    if ab_row.empty:
        raise ValueError("Could not find 'Alberta' row in housing starts file.")
    ab_row = ab_row.drop(columns=["Geography"])

    df = (
        ab_row.melt(var_name="period_label", value_name="starts_saar_units")
             .dropna(subset=["starts_saar_units"])
             .copy()
    )

    df["date"] = pd.to_datetime(df["period_label"].astype(str) + "-01",
                                format="%b-%y-%d", errors="coerce") + pd.offsets.MonthEnd(0)
    df["starts_saar_units"] = pd.to_numeric(df["starts_saar_units"], errors="coerce")

    starts_monthly = df[["date", "starts_saar_units"]].sort_values("date").reset_index(drop=True)
    starts_quarterly = (
        starts_monthly.set_index("date").resample("Q").mean(numeric_only=True).reset_index()
                      .rename(columns={"date": "quarter"})
    )

    starts_monthly.to_csv(PROC_DIR / "ab_housing_starts_monthly.csv", index=False)
    starts_quarterly.to_csv(PROC_DIR / "ab_housing_starts_quarterly_avg.csv", index=False)
    return starts_monthly, starts_quarterly


# ---------------------------------------------------------------------
# 3. International migration (Alberta, quarterly)
# ---------------------------------------------------------------------
def clean_international_migration(file_path: Path) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Clean international migration components for Alberta.

    Input columns expected (case/space-insensitive):
    - Reference period (e.g., 'Q1 2025')
    - Immigrants
    - Net emigration
    - Net non-permanent residents

    Returns
    -------
    mig_quarterly_wide : DataFrame with columns:
        quarter, immigrants, net_non_permanent_residents, net_emigration, total_pressure
    mig_quarterly_long : Long format for plotting.
    """
    df = pd.read_csv(file_path)
    df.columns = df.columns.str.strip().str.lower().str.replace(r"[^\w]+", "_", regex=True)

    q_as_period = df["reference_period"].str.strip().str.replace(r"Q(\d)\s+(\d{4})", r"\2Q\1", regex=True)
    df["quarter"] = pd.PeriodIndex(q_as_period, freq="Q").to_timestamp("Q")

    num_cols = ["immigrants", "net_emigration", "net_non_permanent_residents"]
    df[num_cols] = (
        df[num_cols].astype(str).replace({"..": np.nan, "...": np.nan})
          .apply(lambda col: pd.to_numeric(col.str.replace(",", "", regex=False), errors="coerce"))
    )

    df["total_pressure"] = df["immigrants"] + df["net_non_permanent_residents"]

    mig_quarterly_wide = (
        df[["quarter", "immigrants", "net_non_permanent_residents", "net_emigration", "total_pressure"]]
          .sort_values("quarter").reset_index(drop=True)
    )
    mig_quarterly_long = (
        mig_quarterly_wide.melt(id_vars="quarter", var_name="component", value_name="value")
                          .assign(geo="Alberta")[["geo", "quarter", "component", "value"]]
                          .sort_values(["quarter", "component"]).reset_index(drop=True)
    )

    mig_quarterly_wide.to_csv(PROC_DIR / "ab_international_migration_quarterly_wide.csv", index=False)
    mig_quarterly_long.to_csv(PROC_DIR / "ab_international_migration_quarterly_long.csv", index=False)
    return mig_quarterly_wide, mig_quarterly_long


# ---------------------------------------------------------------------
# 4. CREA MLS® HPI (monthly → quarterly)
# ---------------------------------------------------------------------
def clean_hpi(file_path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Read Excel with sheets 'ALBERTA', 'CALGARY', 'EDMONTON' and compute quarterly means.

    Returns
    -------
    hpi_monthly_all : stacked monthly panel
    hpi_quarterly_all : quarterly means with column 'quarter'
    """
    sheets = {"ALBERTA": "Alberta", "CALGARY": "Calgary", "EDMONTON": "Edmonton"}
    frames = []
    for sheet_name, geo_label in sheets.items():
        df = pd.read_excel(file_path, sheet_name=sheet_name)
        df.columns = (
            df.columns.astype(str).str.strip().str.lower().str.replace(r"[^\w]+", "_", regex=True)
        )
        df["date"] = pd.to_datetime(df["date"], format="%b %Y") + pd.offsets.MonthEnd(0)
        df["geo"] = geo_label
        for c in df.columns:
            if c not in ["geo", "date"]:
                df[c] = pd.to_numeric(df[c], errors="coerce")
        frames.append(df[["geo", "date"] + [c for c in df.columns if c not in ("geo", "date")]])

    hpi_monthly_all = pd.concat(frames, ignore_index=True).sort_values(["geo", "date"]).reset_index(drop=True)
    tmp = hpi_monthly_all.set_index("date")
    numeric_cols = tmp.drop(columns=["geo"]).select_dtypes(include=["number"]).columns

    hpi_quarterly_all = (
        tmp.groupby("geo")[numeric_cols].resample("QE").mean().reset_index().rename(columns={"date": "quarter"})
          .sort_values(["geo", "quarter"]).reset_index(drop=True)
    )

    hpi_monthly_all.to_csv(PROC_DIR / "hpi_monthly_clean.csv", index=False)
    hpi_quarterly_all.to_csv(PROC_DIR / "hpi_quarterly_avg.csv", index=False)
    return hpi_monthly_all, hpi_quarterly_all


# ---------------------------------------------------------------------
# 5. Interprovincial migration (Alberta, quarterly)
# ---------------------------------------------------------------------
def clean_interprov_migration(file_path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Clean interprovincial in/out/ net migration for Alberta from a 2-row CSV.

    The CSV is expected with first column as the flow label ('In-migrants','Out-migrants')
    and subsequent columns as 'Q1 2024', 'Q2 2024', ... values (may include commas).

    Returns
    -------
    long : DataFrame long format [flow_type, quarter_label, people, quarter]
    wide : DataFrame wide format [quarter, interprov_in, interprov_out, interprov_net]
    """
    df = pd.read_csv(file_path)

    df = df.iloc[1:3].reset_index(drop=True)
    df = df.rename(columns={df.columns[0]: "flow_type"})

    long = df.melt(id_vars="flow_type", var_name="quarter_label", value_name="people")
    long["people"] = (
        long["people"].astype(str).str.replace(",", "", regex=False).str.strip().astype(float)
    )

    def to_q_end(lbl: str) -> pd.Timestamp:
        q, year = lbl.strip().split()
        qnum = int(q.replace("Q", ""))
        month = qnum * 3
        return pd.Timestamp(year=int(year), month=month, day=1) + pd.offsets.MonthEnd(0)

    long["quarter"] = long["quarter_label"].apply(to_q_end)

    wide = long.pivot(index="quarter", columns="flow_type", values="people").reset_index()
    norm_cols = {c: str(c).strip().lower().replace("\u00a0", " ") for c in wide.columns}
    wide = wide.rename(columns=norm_cols)

    rename_map = {}
    for c in wide.columns:
        if "in-migrants" in c:
            rename_map[c] = "interprov_in"
        elif "out-migrants" in c:
            rename_map[c] = "interprov_out"
    wide = wide.rename(columns=rename_map)
    if "interprov_in" not in wide.columns:
        wide["interprov_in"] = 0.0
    if "interprov_out" not in wide.columns:
        wide["interprov_out"] = 0.0

    wide["interprov_net"] = wide["interprov_in"] - wide["interprov_out"]
    wide = wide.sort_values("quarter").reset_index(drop=True)

    long.to_csv(PROC_DIR / "interprovincial_migration_long.csv", index=False)
    wide.to_csv(PROC_DIR / "interprovincial_migration_quarterly.csv", index=False)
    return long, wide

