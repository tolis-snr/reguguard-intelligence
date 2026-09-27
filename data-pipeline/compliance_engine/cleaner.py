"""
Data Hygiene & Sanitization Module.
Responsible for cleaning nulls, stripping strings, and standardizing data types.
"""

import logging
import pandas as pd

logger = logging.getLogger("compliance_engine.cleaner")


def clean_financial_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Sanitizes raw corporate financial records by handling missing values,
    trimming strings, and flagging baseline data quality anomalies.
    """
    logger.info("Sanitizing corporate financial dataset...")
    clean_df = df.copy()

    # Strip whitespace from string columns
    string_cols = clean_df.select_dtypes(include=["object"]).columns
    for col in string_cols:
        clean_df[col] = clean_df[col].astype(str).str.strip()

    # Handle missing identifiers
    clean_df["registration_number"] = clean_df["registration_number"].replace(
        ["nan", "None", ""], "UNREGISTERED"
    )

    # Handle undisclosed ownership
    clean_df["beneficial_owner"] = clean_df["beneficial_owner"].replace(
        ["nan", "None", "", "UNKNOWN"], "NOT_DISCLOSED"
    )

    # Safe defaults for financial metrics
    clean_df["annual_revenue_mil"] = clean_df["annual_revenue_mil"].fillna(0.0)
    clean_df["debt_to_equity_ratio"] = clean_df["debt_to_equity_ratio"].fillna(0.0)

    logger.info("Successfully sanitized %d financial records.", len(clean_df))
    return clean_df