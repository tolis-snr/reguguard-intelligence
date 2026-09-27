"""
Entity Resolution Module.
Cross-references corporate entities and ultimate beneficial owners against sanctions feeds.
"""

import logging
import pandas as pd

logger = logging.getLogger("compliance_engine.resolver")


def perform_entity_resolution(financials_df: pd.DataFrame, sanctions_df: pd.DataFrame) -> pd.DataFrame:
    """
    Cross-references corporate entities and ultimate beneficial owners (UBOs)
    against international watchlists using a two-tier left merge.

    Business Rationale & Mechanism Example:
    --------------------------------------
    A company can be non-compliant in two distinct ways:
      1. Direct Corporate Match (ORGANIZATION): The company itself is sanctioned.
      2. Beneficial Ownership Match (INDIVIDUAL): The company is clean, but its owner is sanctioned.

    Trace Example:
    --------------
    Input Financials:
      - COMP-1: Acme Clean Ltd      | Owner: Alice Green
      - COMP-2: Narco Logistics SA  | Owner: Bob White
      - COMP-3: Sunny Bakery LLC    | Owner: Dmitri Boss

    Input Watchlist:
      - Narco Logistics SA (TARGET: ORGANIZATION | SEVERITY: HIGH)
      - Dmitri Boss        (TARGET: INDIVIDUAL   | SEVERITY: CRITICAL)

    Execution Steps:
      Step 1 (Org Merge): Matches 'Narco Logistics SA' via company_name -> HIGH
      Step 2 (Ind Merge): Matches 'Dmitri Boss' via beneficial_owner    -> CRITICAL
      Step 3 (Coalesce):  Combines matches into 'matched_sanction_severity':
                          COMP-1 -> NONE     (Clean entity)
                          COMP-2 -> HIGH     (Direct organization hit)
                          COMP-3 -> CRITICAL (Indirect owner hit)

    Returns:
        pd.DataFrame: Enriched dataframe containing consolidated sanction hit flags
                      and severity levels.
    """
    logger.info("Cross-referencing entities against active sanctions feeds...")

    # 1. Segregate sanctions into Organizations and Individuals for precise joins
    org_sanctions = sanctions_df[sanctions_df["target_type"] == "ORGANIZATION"].copy()
    ind_sanctions = sanctions_df[sanctions_df["target_type"] == "INDIVIDUAL"].copy()

    # 2. Match 1: Corporate Entity match (Company Name <-> Entity Name)
    merged_org = pd.merge(
        financials_df,
        org_sanctions[["entity_name", "severity", "sanction_program", "sanction_id"]],
        left_on="company_name",
        right_on="entity_name",
        how="left"
    )

    # 3. Match 2: Beneficial Owner match (Beneficial Owner <-> Entity Name)
    merged_all = pd.merge(
        merged_org,
        ind_sanctions[["entity_name", "severity", "sanction_program", "sanction_id"]],
        left_on="beneficial_owner",
        right_on="entity_name",
        how="left",
        suffixes=("_org_match", "_ind_match")
    )

    # 4. Consolidate flags (True if matched either on company or owner)
    merged_all["has_sanction_hit"] = (
        merged_all["severity_org_match"].notna() | merged_all["severity_ind_match"].notna()
    )

    # 5. Coalesce severity levels (prioritizes org match, falls back to owner match)
    merged_all["matched_sanction_severity"] = merged_all["severity_org_match"].combine_first(
        merged_all["severity_ind_match"]
    ).fillna("NONE")

    merged_all["matched_sanction_id"] = merged_all["sanction_id_org_match"].combine_first(
        merged_all["sanction_id_ind_match"]
    ).fillna("N/A")

    # 6. Drop intermediate merge artifacts
    cleanup_cols = [
        "entity_name_org_match", "severity_org_match", "sanction_program_org_match", "sanction_id_org_match",
        "entity_name_ind_match", "severity_ind_match", "sanction_program_ind_match", "sanction_id_ind_match"
    ]
    resolved_df = merged_all.drop(columns=cleanup_cols)

    logger.info("Entity resolution complete. Watchlist hits recorded.")
    return resolved_df