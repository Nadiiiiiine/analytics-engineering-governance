import pandas as pd
import numpy as np
from faker import Faker
import random
import os
import duckdb

fake = Faker('fr_FR')  # pour des données en français (mais les montants en €)
Faker.seed(42)
random.seed(42)
np.random.seed(42)

# Paramètres
n_customers = 500
n_branches = 20
n_products = 10
n_accounts = 800
n_transactions = 10000
n_loans = 200
n_cards = 300

# 1. Branches
branches = pd.DataFrame({
    'branch_id': range(1, n_branches+1),
    'branch_name': [fake.company() for _ in range(n_branches)],
    'city': [fake.city() for _ in range(n_branches)],
    'postcode': [fake.postcode() for _ in range(n_branches)],
    'opening_date': [fake.date_between(start_date='-10y', end_date='today') for _ in range(n_branches)]
})

# 2. Référentiel postaux (pour enrichir)
postcodes = pd.DataFrame({
    'postcode': branches['postcode'].unique(),
    'city': [fake.city() for _ in range(len(branches['postcode'].unique()))],
    'region': [fake.region() for _ in range(len(branches['postcode'].unique()))]
})

# 3. Référentiel produits
products = pd.DataFrame({
    'product_id': range(1, n_products+1),
    'product_name': ['Compte Courant', 'Livret A', 'PEL', 'Assurance Vie', 'Crédit Conso', 'Crédit Immobilier', 'Carte Gold', 'Carte Premium', 'Pack Jeune', 'Pack Sénior'],
    'product_type': ['Account', 'Account', 'Account', 'Insurance', 'Loan', 'Loan', 'Card', 'Card', 'Account', 'Account']
})

# 4. Customers
customers = pd.DataFrame({
    'customer_id': range(1, n_customers+1),
    'first_name': [fake.first_name() for _ in range(n_customers)],
    'last_name': [fake.last_name() for _ in range(n_customers)],
    'email': [fake.email() for _ in range(n_customers)],
    'phone': [fake.phone_number() for _ in range(n_customers)],
    'dob': [fake.date_of_birth(minimum_age=18, maximum_age=90) for _ in range(n_customers)],
    'city': [fake.city() for _ in range(n_customers)],
    'postcode': [fake.postcode() for _ in range(n_customers)],
    'registration_date': [fake.date_between(start_date='-5y', end_date='today') for _ in range(n_customers)],
    'branch_id': [random.choice(branches['branch_id']) for _ in range(n_customers)]
})

# 5. Accounts
accounts = pd.DataFrame({
    'account_id': range(1, n_accounts+1),
    'customer_id': [random.choice(customers['customer_id']) for _ in range(n_accounts)],
    'branch_id': [random.choice(branches['branch_id']) for _ in range(n_accounts)],
    'product_id': [random.choice([1,2,3,4,9,10]) for _ in range(n_accounts)],  # seulement comptes
    'balance': [round(random.uniform(-500, 10000), 2) for _ in range(n_accounts)],
    'currency': 'EUR',
    'opening_date': [fake.date_between(start_date='-5y', end_date='today') for _ in range(n_accounts)],
    'status': [random.choice(['active', 'active', 'active', 'dormant', 'closed']) for _ in range(n_accounts)]
})

# 6. Transactions
transactions = pd.DataFrame({
    'transaction_id': range(1, n_transactions+1),
    'account_id': [random.choice(accounts['account_id']) for _ in range(n_transactions)],
    'amount': [round(random.uniform(-1000, 1000), 2) for _ in range(n_transactions)],
    'currency': 'EUR',
    'transaction_date': [fake.date_between(start_date='-1y', end_date='today') for _ in range(n_transactions)],
    'description': [fake.sentence() for _ in range(n_transactions)],
    'type': [random.choice(['credit', 'debit']) for _ in range(n_transactions)]
})

# 7. Loans
loans = pd.DataFrame({
    'loan_id': range(1, n_loans+1),
    'customer_id': [random.choice(customers['customer_id']) for _ in range(n_loans)],
    'branch_id': [random.choice(branches['branch_id']) for _ in range(n_loans)],
    'product_id': [random.choice([5,6]) for _ in range(n_loans)],
    'amount': [round(random.uniform(1000, 200000), 2) for _ in range(n_loans)],
    'interest_rate': [round(random.uniform(1.5, 6.0), 2) for _ in range(n_loans)],
    'start_date': [fake.date_between(start_date='-5y', end_date='today') for _ in range(n_loans)],
    'end_date': [fake.date_between(start_date='+1y', end_date='+10y') for _ in range(n_loans)],
    'status': [random.choice(['ongoing', 'paid', 'default']) for _ in range(n_loans)]
})

# 8. Cards
cards = pd.DataFrame({
    'card_id': range(1, n_cards+1),
    'account_id': [random.choice(accounts['account_id']) for _ in range(n_cards)],
    'product_id': [random.choice([7,8]) for _ in range(n_cards)],
    'card_number': [fake.credit_card_number() for _ in range(n_cards)],
    'expiry_date': [fake.credit_card_expire() for _ in range(n_cards)],
    'cvv': [fake.credit_card_security_code() for _ in range(n_cards)],
    'issue_date': [fake.date_between(start_date='-3y', end_date='today') for _ in range(n_cards)],
    'status': [random.choice(['active', 'blocked', 'expired']) for _ in range(n_cards)]
})

# Sauvegarde en CSV
os.makedirs('data', exist_ok=True)
branches.to_csv('data/branches.csv', index=False)
postcodes.to_csv('data/reference_postcodes.csv', index=False)
products.to_csv('data/reference_products.csv', index=False)
customers.to_csv('data/customers.csv', index=False)
accounts.to_csv('data/accounts.csv', index=False)
transactions.to_csv('data/transactions.csv', index=False)
loans.to_csv('data/loans.csv', index=False)
cards.to_csv('data/cards.csv', index=False)

# Chargement dans DuckDB
duckdb.sql("CREATE OR REPLACE TABLE branches AS SELECT * FROM read_csv_auto('data/branches.csv');")
duckdb.sql("CREATE OR REPLACE TABLE reference_postcodes AS SELECT * FROM read_csv_auto('data/reference_postcodes.csv');")
duckdb.sql("CREATE OR REPLACE TABLE reference_products AS SELECT * FROM read_csv_auto('data/reference_products.csv');")
duckdb.sql("CREATE OR REPLACE TABLE customers AS SELECT * FROM read_csv_auto('data/customers.csv');")
duckdb.sql("CREATE OR REPLACE TABLE accounts AS SELECT * FROM read_csv_auto('data/accounts.csv');")
duckdb.sql("CREATE OR REPLACE TABLE transactions AS SELECT * FROM read_csv_auto('data/transactions.csv');")
duckdb.sql("CREATE OR REPLACE TABLE loans AS SELECT * FROM read_csv_auto('data/loans.csv');")
duckdb.sql("CREATE OR REPLACE TABLE cards AS SELECT * FROM read_csv_auto('data/cards.csv');")

# Export en Parquet (optionnel)
for table in ['branches','reference_postcodes','reference_products','customers','accounts','transactions','loans','cards']:
    duckdb.sql(f"COPY {table} TO 'data/{table}.parquet' (FORMAT PARQUET);")

print("✅ Dataset généré et chargé dans DuckDB (fichiers CSV et Parquet dans ./data/)")
