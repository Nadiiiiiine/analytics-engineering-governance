"""Generate a coherent synthetic banking dataset, inject controlled defects,
and load the result into the raw schema of a local DuckDB warehouse.

The whole "world" is simulated once up to WORLD_END. An extract only shows
what was visible on its date, so day1 and day2 share the same ids and the
same history, exactly like two daily loads from a real source system.

Usage:
     poetry run python generator/generate_dataset.py --extract day1
     poetry run python generator/generate_dataset.py --extract day2
"""

from __future__ import annotations

import argparse
import unicodedata
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from faker import Faker

from anomalies import inject_anomalies

SEED = 42
EXTRACTS = {"day1": date(2026, 6, 30), "day2": date(2026, 7, 31)}
WORLD_END = max(EXTRACTS.values())
HISTORY_START = date(2023, 1, 1)
N_CUSTOMERS = 500
N_LOANS = 150

ROOT = Path(__file__).resolve().parents[1]
SEEDS_DIR = ROOT / "seeds"
WAREHOUSE = ROOT / "warehouse.duckdb"

EMAIL_DOMAINS = ["gmail.com", "outlook.fr", "orange.fr", "free.fr", "yahoo.fr"]
CARD_SPEND = {  # category: (share, min amount, max amount, merchants)
    "groceries": (0.40, 15, 120, ["Carrefour", "Monoprix", "Lidl", "Picard"]),
    "restaurants": (0.20, 10, 80, ["Brasserie du Coin", "Sushi Shop", "Big Fernand"]),
    "transport": (0.15, 2, 60, ["SNCF", "RATP", "TotalEnergies", "Uber"]),
    "shopping": (0.15, 20, 250, ["Fnac", "Decathlon", "Zara", "Amazon"]),
    "utilities": (0.10, 30, 150, ["EDF", "Free Mobile", "Engie", "Orange"]),
}


# ---------------------------------------------------------------- helpers
def rand_date(rng: np.random.Generator, start: date, end: date) -> date:
    """Uniform random date between start and end, both included."""
    return start + timedelta(days=int(rng.integers(0, (end - start).days + 1)))


def at(day: date, hour: int, minute: int = 0) -> datetime:
    return datetime.combine(day, time(hour, minute))


def add_months(day: date, months: int) -> date:
    return (pd.Timestamp(day) + pd.DateOffset(months=months)).date()


def month_starts(start: date, end: date) -> list[date]:
    first = date(start.year, start.month, 1)
    return [d.date() for d in pd.date_range(first, end, freq="MS")]


def present(value) -> bool:
    """True for a real value, False for None / NaN / NaT."""
    return value is not None and not pd.isna(value)


def slug(text: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return "".join(ch for ch in ascii_text.lower() if ch.isalnum())


# ---------------------------------------------------------------- world
def build_branches(rng, postcodes: pd.DataFrame) -> pd.DataFrame:
    branches = postcodes.reset_index(drop=True).copy()
    branches.insert(0, "branch_id", range(1, len(branches) + 1))
    branches["branch_name"] = "Agence " + branches["city"]
    branches["opening_date"] = [
        rand_date(rng, date(2010, 1, 1), date(2020, 12, 31)) for _ in range(len(branches))
    ]
    return branches[["branch_id", "branch_name", "city", "postcode", "region", "opening_date"]]


def pick_home(rng, postcodes: pd.DataFrame, branches: pd.DataFrame, exclude_region=None):
    """A postcode and a branch of the same region."""
    candidates = postcodes if exclude_region is None else postcodes[postcodes.region != exclude_region]
    pc = candidates.iloc[int(rng.integers(len(candidates)))]
    region_branches = branches.loc[branches.region == pc.region, "branch_id"].to_numpy()
    return pc, int(rng.choice(region_branches))


def build_customers(rng, fake: Faker, postcodes, branches) -> pd.DataFrame:
    rows = []
    for customer_id in range(1, N_CUSTOMERS + 1):
        first, last = fake.first_name(), fake.last_name()
        registered = rand_date(rng, HISTORY_START, WORLD_END - timedelta(days=10))
        pc, branch_id = pick_home(rng, postcodes, branches)
        row = {
            "customer_id": customer_id,
            "first_name": first,
            "last_name": last,
            "email": f"{slug(first)}.{slug(last)}{customer_id}@{str(rng.choice(EMAIL_DOMAINS))}",
            "phone": fake.phone_number(),
            "dob": registered - timedelta(days=int(rng.integers(18 * 365, 85 * 365))),
            "postcode": pc.postcode,
            "city": pc.city,
            "branch_id": branch_id,
            "registration_date": registered,
            "updated_at": at(registered, 8, int(rng.integers(0, 60))),
        }
        # 6% move to another region in July 2026, between the two extracts
        if rng.random() < 0.06 and registered < EXTRACTS["day1"]:
            new_pc, new_branch = pick_home(rng, postcodes, branches, exclude_region=pc.region)
            moved = rand_date(rng, EXTRACTS["day1"] + timedelta(days=1), WORLD_END)
            row["move"] = (moved, new_pc.postcode, new_pc.city, new_branch)
        rows.append(row)
    return pd.DataFrame(rows)


def current_product(age: int) -> int:
    if age < 26:
        return 9  # Pack Jeune
    if age >= 65:
        return 10  # Pack Senior
    return 1  # Compte Courant


def build_accounts(rng, customers: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for c in customers.itertuples():
        age = (c.registration_date - c.dob).days // 365
        rows.append(
            {"customer_id": c.customer_id, "branch_id": c.branch_id,
             "product_id": current_product(age), "opening_date": c.registration_date,
             "kind": "current"}
        )
        if rng.random() < 0.55 and c.registration_date < WORLD_END - timedelta(days=30):
            rows.append(
                {"customer_id": c.customer_id, "branch_id": c.branch_id,
                 "product_id": 2 if rng.random() < 0.7 else 3,
                 "opening_date": rand_date(rng, c.registration_date, WORLD_END - timedelta(days=1)),
                 "kind": "savings"}
            )
    accounts = pd.DataFrame(rows)
    accounts.insert(0, "account_id", range(1, len(accounts) + 1))
    closing_rate = np.where(accounts.kind == "savings", 0.08, 0.03)
    closes = rng.random(len(accounts)) < closing_rate
    accounts["closed_date"] = [
        rand_date(rng, o + timedelta(days=30), WORLD_END)
        if close and o + timedelta(days=30) < WORLD_END else None
        for close, o in zip(closes, accounts.opening_date)
    ]
    return accounts


def simulate_transactions(rng, accounts: pd.DataFrame) -> pd.DataFrame:
    """Every account starts with an opening deposit, so its balance is
    always the exact sum of its transactions."""
    tx = []

    def add(account_id, ts, amount, category, counterparty):
        amount = round(float(amount), 2)
        if amount != 0:
            tx.append((account_id, ts, amount, category, counterparty))

    for a in accounts.itertuples():
        last_day = a.closed_date if present(a.closed_date) else WORLD_END
        if a.kind == "current":
            income = round(float(np.clip(rng.lognormal(np.log(2400), 0.35), 1300, 9000)), 2)
            add(a.account_id, at(a.opening_date, 10, 30), rng.uniform(100, 2000), "opening_deposit", "Initial deposit")
            for m in month_starts(a.opening_date, last_day):
                salary_day, rent_day = m.replace(day=28), m.replace(day=5)
                if a.opening_date < salary_day <= last_day:
                    add(a.account_id, at(salary_day, 6), income, "salary", "Employer")
                if a.opening_date < rent_day <= last_day:
                    add(a.account_id, at(rent_day, 7), -0.3 * income, "housing", "Landlord")
                for _ in range(int(rng.poisson(6))):
                    day = rand_date(rng, max(m, a.opening_date), min(add_months(m, 1) - timedelta(days=1), last_day))
                    category = str(rng.choice(list(CARD_SPEND), p=[v[0] for v in CARD_SPEND.values()]))
                    _, low, high, merchants = CARD_SPEND[category]
                    add(a.account_id, at(day, int(rng.integers(11, 22)), int(rng.integers(0, 60))),
                        -rng.uniform(low, high), category, str(rng.choice(merchants)))
        else:
            add(a.account_id, at(a.opening_date, 10, 45), rng.uniform(500, 5000), "opening_deposit", "Initial deposit")
            for m in month_starts(a.opening_date, last_day):
                transfer_day = m.replace(day=2)
                if a.opening_date < transfer_day <= last_day and rng.random() < 0.7:
                    add(a.account_id, at(transfer_day, 9), rng.uniform(50, 300), "transfer_in", "Own current account")
        if present(a.closed_date):  # empty the account on its closing day
            balance = round(sum(t[2] for t in tx if t[0] == a.account_id), 2)
            add(a.account_id, at(a.closed_date, 23, 0), -balance, "account_closure", "Closing transfer")

    df = pd.DataFrame(tx, columns=["account_id", "transaction_ts", "amount", "category", "counterparty"])
    df = df.sort_values(["transaction_ts", "account_id"], kind="stable").reset_index(drop=True)
    df.insert(0, "transaction_id", range(1, len(df) + 1))
    df["type"] = np.where(df.amount > 0, "credit", "debit")
    df["currency"] = "EUR"
    return df


def build_cards(rng, fake: Faker, accounts: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for a in accounts[accounts.kind == "current"].itertuples():
        if rng.random() > 0.75:
            continue
        issued = min(a.opening_date + timedelta(days=int(rng.integers(0, 21))), WORLD_END)
        if present(a.closed_date):
            issued = min(issued, a.closed_date)
        expires = add_months(issued, 36)
        blocked = rand_date(rng, issued, WORLD_END) if rng.random() < 0.04 else None
        rows.append({
            "account_id": a.account_id,
            "product_id": 7 if rng.random() < 0.3 else 8,
            "card_number": fake.credit_card_number(),
            "cvv": fake.credit_card_security_code(),
            "expiry_date": expires.strftime("%m/%y"),
            "expires_on": expires,
            "issue_date": issued,
            "blocked_date": blocked,
            "cancelled_date": a.closed_date,
        })
    cards = pd.DataFrame(rows)
    cards.insert(0, "card_id", range(1, len(cards) + 1))
    return cards


def build_loans(rng, customers: pd.DataFrame) -> pd.DataFrame:
    rows = []
    eligible = customers[customers.registration_date < WORLD_END - timedelta(days=60)]
    for loan_id in range(1, N_LOANS + 1):
        c = eligible.iloc[int(rng.integers(len(eligible)))]
        start = rand_date(rng, c.registration_date + timedelta(days=30), WORLD_END - timedelta(days=1))
        if rng.random() < 0.65:
            product_id, term = 5, int(rng.choice([12, 24, 36, 48, 60, 84]))
            principal, rate = round(rng.uniform(1_000, 40_000), -2), round(rng.uniform(2.5, 7.0), 2)
        else:
            product_id, term = 6, int(rng.choice([120, 180, 240, 300]))
            principal, rate = round(rng.uniform(50_000, 400_000), -3), round(rng.uniform(1.8, 4.5), 2)
        end = add_months(start, term)
        default_date = paid_date = None
        if rng.random() < 0.06 and start + timedelta(days=90) < WORLD_END:
            default_date = rand_date(rng, start + timedelta(days=90), WORLD_END)
        elif end <= WORLD_END:
            paid_date = end
        elif rng.random() < 0.05 and start + timedelta(days=180) < WORLD_END:
            paid_date = rand_date(rng, start + timedelta(days=180), WORLD_END)  # early repayment
        rows.append({
            "loan_id": loan_id, "customer_id": int(c.customer_id), "branch_id": int(c.branch_id),
            "product_id": product_id, "principal_amount": principal, "interest_rate": rate,
            "term_months": term, "start_date": start, "end_date": end,
            "default_date": default_date, "paid_date": paid_date,
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- extract
def extract(world: dict[str, pd.DataFrame], as_of: date) -> dict[str, pd.DataFrame]:
    """What the source system shows on `as_of`."""
    cust = world["customers"]
    cust = cust[cust.registration_date <= as_of].copy()
    for i, row in cust.iterrows():
        move = row.get("move")
        if isinstance(move, tuple) and move[0] <= as_of:
            moved, postcode, city, branch_id = move
            cust.loc[i, ["postcode", "city", "branch_id", "updated_at"]] = [postcode, city, branch_id, at(moved, 9)]
    customers = cust.drop(columns="move", errors="ignore")

    tx = world["transactions"]
    transactions = tx[tx.transaction_ts.dt.date <= as_of].copy()

    acc = world["accounts"]
    acc = acc[acc.opening_date <= as_of].copy()
    acc["closed_date"] = [d if present(d) and d <= as_of else None for d in acc.closed_date]
    acc["status"] = np.where(acc.closed_date.notna(), "closed", "active")
    balances = transactions.groupby("account_id").amount.sum().round(2)
    acc["balance"] = acc.account_id.map(balances).fillna(0.0)
    acc["currency"] = "EUR"
    acc["updated_at"] = [at(c if present(c) else o, 23, 30) for c, o in zip(acc.closed_date, acc.opening_date)]
    accounts = acc[["account_id", "customer_id", "branch_id", "product_id", "balance", "currency",
                    "opening_date", "closed_date", "status", "updated_at"]]

    cards = world["cards"]
    cards = cards[cards.issue_date <= as_of].copy()

    def card_status(r):
        if present(r.cancelled_date) and r.cancelled_date <= as_of:
            return "cancelled", r.cancelled_date
        if present(r.blocked_date) and r.blocked_date <= as_of:
            return "blocked", r.blocked_date
        if r.expires_on < as_of:
            return "expired", r.expires_on
        return "active", r.issue_date

    states = cards.apply(card_status, axis=1, result_type="expand")
    cards["status"], cards["updated_at"] = states[0], [at(d, 12) for d in states[1]]
    cards = cards[["card_id", "account_id", "product_id", "card_number", "cvv", "expiry_date",
                   "issue_date", "status", "updated_at"]]

    loans = world["loans"]
    loans = loans[loans.start_date <= as_of].copy()

    def loan_status(r):
        if present(r.default_date) and r.default_date <= as_of:
            return "default", r.default_date
        if present(r.paid_date) and r.paid_date <= as_of:
            return "paid", r.paid_date
        return "ongoing", r.start_date

    states = loans.apply(loan_status, axis=1, result_type="expand")
    loans["status"], loans["updated_at"] = states[0], [at(d, 12) for d in states[1]]
    loans = loans[["loan_id", "customer_id", "branch_id", "product_id", "principal_amount",
                   "interest_rate", "term_months", "start_date", "end_date", "status", "updated_at"]]

    branches = world["branches"].drop(columns="region")
    return {"branches": branches, "customers": customers, "accounts": accounts,
            "transactions": transactions[["transaction_id", "account_id", "transaction_ts", "amount",
                                          "currency", "type", "category", "counterparty"]],
            "cards": cards, "loans": loans}


# ---------------------------------------------------------------- load
def load_to_duckdb(tables: dict[str, pd.DataFrame], as_of: date) -> None:
    import duckdb

    loaded_at = datetime.now(timezone.utc).replace(tzinfo=None)
    with duckdb.connect(str(WAREHOUSE)) as con:
        con.execute("create schema if not exists raw")
        for name, df in tables.items():
            incoming = df.assign(_extract_date=as_of, _loaded_at=loaded_at)
            con.register("incoming", incoming)
            con.execute(f"create or replace table raw.{name} as select * from incoming")
            con.unregister("incoming")
            print(f"  raw.{name:<16} {len(df):>7,} rows")


def build_world() -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(SEED)
    Faker.seed(SEED)
    fake = Faker("fr_FR")
    postcodes = pd.read_csv(SEEDS_DIR / "reference_postcodes.csv", dtype={"postcode": str})
    branches = build_branches(rng, postcodes)
    customers = build_customers(rng, fake, postcodes, branches)
    accounts = build_accounts(rng, customers)
    return {
        "branches": branches,
        "customers": customers,
        "accounts": accounts,
        "transactions": simulate_transactions(rng, accounts),
        "cards": build_cards(rng, fake, accounts),
        "loans": build_loans(rng, customers),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--extract", choices=EXTRACTS, default="day1")
    parser.add_argument("--no-defects", action="store_true", help="load clean data only")
    args = parser.parse_args()

    as_of = EXTRACTS[args.extract]
    tables = extract(build_world(), as_of)
    if args.no_defects:
        manifest = pd.DataFrame(columns=["rule_id", "table_name", "record_id"])
    else:
        tables, manifest = inject_anomalies(tables, as_of)
    tables["defect_manifest"] = manifest
    print(f"Extract {args.extract} (as of {as_of}) -> {WAREHOUSE.name}")
    load_to_duckdb(tables, as_of)


if __name__ == "__main__":
    main()
