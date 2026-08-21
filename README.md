# Structure de la base de données 

## 1. Tables principales

### `customers` — Clients

| Colonne | Type | Description |
|---|---|---|
| `customer_id` | BIGINT | Identifiant unique du client |
| `first_name` | VARCHAR | Prénom |
| `last_name` | VARCHAR | Nom |
| `email` | VARCHAR | Adresse e-mail |
| `phone` | VARCHAR | Numéro de téléphone |
| `dob` | DATE | Date de naissance |
| `city` | VARCHAR | Ville de résidence |
| `postcode` | VARCHAR | Code postal |
| `registration_date` | DATE | Date d’inscription |
| `branch_id` | BIGINT | Agence associée |

Relation :

```
customers.branch_id → branches.branch_id
```

---

### `accounts` — Comptes bancaires

| Colonne | Type | Description |
|---|---|---|
| `account_id` | BIGINT | Identifiant unique du compte |
| `customer_id` | BIGINT | Client propriétaire |
| `branch_id` | BIGINT | Agence de rattachement |
| `product_id` | BIGINT | Produit bancaire |
| `balance` | DOUBLE | Solde du compte |
| `currency` | VARCHAR | Devise |
| `opening_date` | DATE | Date d’ouverture |
| `status` | VARCHAR | Statut du compte |

Relations :

```
accounts.customer_id → customers.customer_id
accounts.branch_id   → branches.branch_id
accounts.product_id  → reference_products.product_id
```

---

### `transactions` — Transactions bancaires

| Colonne | Type | Description |
|---|---|---|
| `transaction_id` | BIGINT | Identifiant unique de la transaction |
| `account_id` | BIGINT | Compte concerné |
| `amount` | DOUBLE | Montant de la transaction |
| `currency` | VARCHAR | Devise |
| `transaction_date` | DATE | Date de la transaction |
| `description` | VARCHAR | Description de l’opération |
| `type` | VARCHAR | Type de transaction |

Relation :

```
transactions.account_id → accounts.account_id
```

---

### `cards` — Cartes bancaires

| Colonne | Type | Description |
|---|---|---|
| `card_id` | BIGINT | Identifiant unique de la carte |
| `account_id` | BIGINT | Compte associé |
| `product_id` | BIGINT | Produit de la carte |
| `card_number` | VARCHAR | Numéro de carte |
| `expiry_date` | VARCHAR | Date d’expiration |
| `cvv` | VARCHAR | Code de sécurité |
| `issue_date` | DATE | Date d’émission |
| `status` | VARCHAR | Statut de la carte |

Relations :

```
cards.account_id → accounts.account_id
cards.product_id → reference_products.product_id
```

---

### `loans` — Prêts

| Colonne | Type | Description |
|---|---|---|
| `loan_id` | BIGINT | Identifiant unique du prêt |
| `customer_id` | BIGINT | Client emprunteur |
| `branch_id` | BIGINT | Agence responsable |
| `product_id` | BIGINT | Produit de prêt |
| `amount` | DOUBLE | Montant emprunté |
| `interest_rate` | DOUBLE | Taux d’intérêt |
| `start_date` | DATE | Date de début |
| `end_date` | DATE | Date de fin prévue |
| `status` | VARCHAR | Statut du prêt |

Relations :

```
loans.customer_id → customers.customer_id
loans.branch_id   → branches.branch_id
loans.product_id  → reference_products.product_id
```

## 2. Tables de référence

### `branches` — Agences

| Colonne | Type | Description |
|---|---|---|
| `branch_id` | BIGINT | Identifiant unique de l’agence |
| `branch_name` | VARCHAR | Nom de l’agence |
| `city` | VARCHAR | Ville |
| `postcode` | VARCHAR | Code postal |
| `opening_date` | DATE | Date d’ouverture |

Relation géographique probable :

```
branches.postcode → reference_postcodes.postcode
```

---

### `reference_products` — Produits bancaires

| Colonne | Type | Description |
|---|---|---|
| `product_id` | BIGINT | Identifiant du produit |
| `product_name` | VARCHAR | Nom du produit |
| `product_type` | VARCHAR | Type de produit |

Cette table est référencée par :

- `accounts`
- `cards`
- `loans`

---

### `reference_postcodes` — Référentiel géographique

| Colonne | Type | Description |
|---|---|---|
| `postcode` | VARCHAR | Code postal |
| `city` | VARCHAR | Ville |
| `region` | VARCHAR | Région |

## 3. Vue globale des relations

```
                         ┌──────────────────────┐
                         │ reference_postcodes  │
                         │──────────────────────│
                         │ PK postcode          │
                         │ city                 │
                         │ region               │
                         └──────────┬───────────┘
                                    │
                                    │ postcode
                                    ▼
┌──────────────────┐       ┌──────────────────┐
│    customers     │       │     branches     │
│──────────────────│       │──────────────────│
│ PK customer_id   │       │ PK branch_id     │
│ first_name       │       │ branch_name      │
│ last_name        │       │ city             │
│ email            │       │ postcode         │
│ phone            │       │ opening_date     │
│ dob              │       └──────┬───────────┘
│ city             │              │
│ postcode         │              │
│ registration_date│              │
│ FK branch_id     │              │
└───────┬──────────┘              │
        │                         │
        │ customer_id             │ branch_id
        ▼                         ▼
┌──────────────────┐       ┌──────────────────┐
│    accounts      │       │      loans       │
│──────────────────│       │──────────────────│
│ PK account_id    │       │ PK loan_id       │
│ FK customer_id   │       │ FK customer_id   │
│ FK branch_id     │       │ FK branch_id     │
│ FK product_id    │       │ FK product_id    │
│ balance          │       │ amount           │
│ currency         │       │ interest_rate    │
│ opening_date     │       │ start_date       │
│ status           │       │ end_date         │
└───────┬──────────┘       │ status           │
        │                  └──────────────────┘
        │ account_id
        ├──────────────────────────┐
        ▼                          ▼
┌──────────────────┐       ┌──────────────────┐
│     cards        │       │   transactions   │
│──────────────────│       │──────────────────│
│ PK card_id       │       │ PK transaction_id│
│ FK account_id    │       │ FK account_id    │
│ FK product_id    │       │ amount           │
│ card_number      │       │ currency         │
│ expiry_date      │       │ transaction_date │
│ cvv              │       │ description      │
│ issue_date       │       │ type             │
│ status           │       └──────────────────┘
└──────────────────┘

                 ┌────────────────────────┐
                 │  reference_products   │
                 │────────────────────────│
                 │ PK product_id          │
                 │ product_name          │
                 │ product_type          │
                 └───────────┬────────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
          accounts         cards          loans
```

## 4. Version Mermaid du diagramme

```
erDiagram
    CUSTOMERS {
        BIGINT customer_id PK
        VARCHAR first_name
        VARCHAR last_name
        VARCHAR email
        VARCHAR phone
        DATE dob
        VARCHAR city
        VARCHAR postcode
        DATE registration_date
        BIGINT branch_id FK
    }

    BRANCHES {
        BIGINT branch_id PK
        VARCHAR branch_name
        VARCHAR city
        VARCHAR postcode FK
        DATE opening_date
    }

    ACCOUNTS {
        BIGINT account_id PK
        BIGINT customer_id FK
        BIGINT branch_id FK
        BIGINT product_id FK
        DOUBLE balance
        VARCHAR currency
        DATE opening_date
        VARCHAR status
    }

    CARDS {
        BIGINT card_id PK
        BIGINT account_id FK
        BIGINT product_id FK
        VARCHAR card_number
        VARCHAR expiry_date
        VARCHAR cvv
        DATE issue_date
        VARCHAR status
    }

    LOANS {
        BIGINT loan_id PK
        BIGINT customer_id FK
        BIGINT branch_id FK
        BIGINT product_id FK
        DOUBLE amount
        DOUBLE interest_rate
        DATE start_date
        DATE end_date
        VARCHAR status
    }

    TRANSACTIONS {
        BIGINT transaction_id PK
        BIGINT account_id FK
        DOUBLE amount
        VARCHAR currency
        DATE transaction_date
        VARCHAR description
        VARCHAR type
    }

    REFERENCE_PRODUCTS {
        BIGINT product_id PK
        VARCHAR product_name
        VARCHAR product_type
    }

    REFERENCE_POSTCODES {
        VARCHAR postcode PK
        VARCHAR city
        VARCHAR region
    }

    CUSTOMERS ||--o{ ACCOUNTS : owns
    CUSTOMERS ||--o{ LOANS : contracts
    BRANCHES ||--o{ CUSTOMERS : serves
    BRANCHES ||--o{ ACCOUNTS : manages
    BRANCHES ||--o{ LOANS : manages
    ACCOUNTS ||--o{ CARDS : has
    ACCOUNTS ||--o{ TRANSACTIONS : contains
    REFERENCE_PRODUCTS ||--o{ ACCOUNTS : defines
    REFERENCE_PRODUCTS ||--o{ CARDS : defines
    REFERENCE_PRODUCTS ||--o{ LOANS : defines
    REFERENCE_POSTCODES ||--o{ BRANCHES : locates
```
