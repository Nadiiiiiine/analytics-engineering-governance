"""Inject controlled data-quality defects into a clean extract.

Every defect is chosen by a stable hash of (rule, record id), so the same
records are broken in every extract, and each one is written to a manifest.
The manifest is the ground truth the dbt quality framework must match:
every injected defect detected, and nothing else.
"""

from __future__ import annotations

import hashlib
from datetime import date, datetime, time, timedelta

import pandas as pd

# rule_id: (rule name, table, share of rows to break)
RULES = {
    "DQ01": ("duplicate_transaction", "transactions", 0.002),
    "DQ02": ("sign_type_mismatch", "transactions", 0.003),
    "DQ03": ("orphan_transaction", "transactions", 0.001),
    "DQ04": ("transaction_before_account_opening", "transactions", 0.001),
    "DQ05": ("future_transaction", "transactions", 0.0005),
    "DQ06": ("invalid_email", "customers", 0.01),
    "DQ07": ("unknown_postcode", "customers", 0.01),
    "DQ08": ("balance_mismatch", "accounts", 0.02),
    "DQ09": ("loan_end_before_start", "loans", 0.02),
    "DQ10": ("invalid_card_expiry", "cards", 0.01),
}


def stable_hash(rule_id: str, record_id) -> int:
    return int(hashlib.md5(f"{rule_id}:{record_id}".encode()).hexdigest(), 16)


def pick(df: pd.DataFrame, id_col: str, rule_id: str, taken: set) -> pd.Series:
    """Boolean mask of the rows this rule breaks, never reusing a row
    already broken by another rule on the same table."""
    rate = RULES[rule_id][2]
    mask = df[id_col].map(lambda i: stable_hash(rule_id, i) % 1_000_000 < rate * 1_000_000)
    mask &= ~df[id_col].isin(taken)
    taken.update(df.loc[mask, id_col])
    return mask


def inject_anomalies(tables: dict[str, pd.DataFrame], as_of: date):
    tables = {name: df.copy() for name, df in tables.items()}
    manifest: list[tuple[str, str, str]] = []

    def log(rule_id: str, ids) -> None:
        manifest.extend((rule_id, RULES[rule_id][1], str(i)) for i in ids)

    # ---- transactions
    tx = tables["transactions"]
    taken: set = set()

    m = pick(tx, "transaction_id", "DQ02", taken)  # the label lies, the amount is right
    tx.loc[m, "type"] = tx.loc[m, "type"].map({"credit": "debit", "debit": "credit"})
    log("DQ02", tx.loc[m, "transaction_id"])

    opening = tx.account_id.map(tables["accounts"].set_index("account_id").opening_date)
    m = pick(tx, "transaction_id", "DQ04", taken)
    tx.loc[m, "transaction_ts"] = [
        datetime.combine(opening[i] - timedelta(days=1 + stable_hash("DQ04", t) % 60), time(14))
        for i, t in tx.loc[m, "transaction_id"].items()
    ]
    log("DQ04", tx.loc[m, "transaction_id"])

    m = pick(tx, "transaction_id", "DQ05", taken)
    tx.loc[m, "transaction_ts"] = [
        datetime.combine(as_of + timedelta(days=1 + stable_hash("DQ05", t) % 30), time(14))
        for t in tx.loc[m, "transaction_id"]
    ]
    log("DQ05", tx.loc[m, "transaction_id"])

    m = pick(tx, "transaction_id", "DQ01", taken)  # the same row delivered twice
    log("DQ01", tx.loc[m, "transaction_id"])
    tx = pd.concat([tx, tx[m]], ignore_index=True)

    # orphans are extra rows on accounts that do not exist, so real balances stay exact
    n_orphans = max(1, round(len(tx) * RULES["DQ03"][2]))
    first_id = int(tx.transaction_id.max()) + 1
    template = tx[~tx.transaction_id.isin(taken)].iloc[:n_orphans].copy()
    template["transaction_id"] = range(first_id, first_id + n_orphans)
    template["account_id"] = range(900_001, 900_001 + n_orphans)
    log("DQ03", template.transaction_id)
    tables["transactions"] = pd.concat([tx, template], ignore_index=True)

    # ---- customers
    cu = tables["customers"]
    taken = set()
    m = pick(cu, "customer_id", "DQ06", taken)
    cu.loc[m, "email"] = cu.loc[m, "email"].str.replace("@", ".at.", regex=False)
    log("DQ06", cu.loc[m, "customer_id"])
    m = pick(cu, "customer_id", "DQ07", taken)
    cu.loc[m, "postcode"] = [f"99{stable_hash('DQ07', c) % 1000:03d}" for c in cu.loc[m, "customer_id"]]
    log("DQ07", cu.loc[m, "customer_id"])

    # ---- accounts
    ac = tables["accounts"]
    m = pick(ac, "account_id", "DQ08", set())
    ac.loc[m, "balance"] = [
        round(b + 5 + stable_hash("DQ08", a) % 500, 2)
        for a, b in zip(ac.loc[m, "account_id"], ac.loc[m, "balance"])
    ]
    log("DQ08", ac.loc[m, "account_id"])

    # ---- loans
    lo = tables["loans"]
    m = pick(lo, "loan_id", "DQ09", set())
    lo.loc[m, "end_date"] = [
        s - timedelta(days=1 + stable_hash("DQ09", i) % 365)
        for i, s in zip(lo.loc[m, "loan_id"], lo.loc[m, "start_date"])
    ]
    log("DQ09", lo.loc[m, "loan_id"])

    # ---- cards
    ca = tables["cards"]
    m = pick(ca, "card_id", "DQ10", set())
    ca.loc[m, "expiry_date"] = "13/" + ca.loc[m, "expiry_date"].str[-2:]
    log("DQ10", ca.loc[m, "card_id"])

    manifest_df = pd.DataFrame(manifest, columns=["rule_id", "table_name", "record_id"])
    print("Injected defects:", manifest_df.rule_id.value_counts().sort_index().to_dict())
    return tables, manifest_df
