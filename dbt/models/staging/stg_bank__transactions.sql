with source as (
    select * from {{ source('bank', 'transactions') }}
)

select
    cast(transaction_id as bigint) as transaction_id,
    cast(account_id as bigint) as account_id,
    cast(transaction_ts as timestamp) as transaction_ts,
    cast(transaction_ts as date) as transaction_date,
    cast(amount as decimal(18, 2)) as amount,
    lower(type) as direction,
    category,
    counterparty,
    currency,
    cast(_extract_date as date) as extract_date,
    cast(_loaded_at as timestamp) as loaded_at
from source
-- no deduplication here: duplicates must stay visible to the quality rules
