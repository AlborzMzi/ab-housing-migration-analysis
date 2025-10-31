"""
Run the full cleaning pipeline from raw files into data/processed.

Usage:
    python scripts/run_pipeline.py
"""

from pathlib import Path
from ab_housing.cleaning import (
    clean_boc_policy_rate,
    clean_housing_starts,
    clean_international_migration,
    clean_hpi,
    clean_interprov_migration,
)

REPO_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = REPO_DIR / "data" / "raw"

# Update these filenames to match what you upload into data/raw/
FILE_BOC = RAW_DIR / "Canadian Policy Rate BoC.csv"
FILE_STARTS = RAW_DIR / "housing starts statcan.csv"
FILE_MIGRATION = RAW_DIR / "Alberta_international_migration_quarterly_clean.csv"
FILE_HPI = RAW_DIR / "MLS HPI SA.xlsx"
FILE_INTERPROV = RAW_DIR / "Interprovincial migration.csv"


def main():
    print("Cleaning BoC policy rate...")
    clean_boc_policy_rate(FILE_BOC)

    print("Cleaning housing starts...")
    clean_housing_starts(FILE_STARTS)

    print("Cleaning international migration...")
    clean_international_migration(FILE_MIGRATION)

    print("Cleaning HPI...")
    clean_hpi(FILE_HPI)

    print("Cleaning interprovincial migration...")
    clean_interprov_migration(FILE_INTERPROV)

    print("Done. Clean files written to data/processed/.")

if __name__ == "__main__":
    main()

