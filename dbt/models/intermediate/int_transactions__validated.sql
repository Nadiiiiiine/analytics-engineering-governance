-- Transactions that are safe to report on: one row per transaction_id,
-- with every quarantined record removed.

with deduplicated as (
    select
        *,
        row_number() over (partition by transaction_id order by loaded_at) as row_num
    from {{ ref('stg_bank__transactions') }}
)

select
    transaction_id,
    account_id,
    transaction_ts,
    transaction_date,
    amount,
    direction,
    category,
    counterparty,
    currency,
    extract_date
from deduplicated
where
    row_num = 1
    and {{ quarantine_filter('transactions', 'transaction_id') }}
