with source as (
    select * from {{ source('bank', 'accounts') }}
)

select
    cast(account_id as bigint) as account_id,
    cast(customer_id as bigint) as customer_id,
    cast(branch_id as bigint) as branch_id,
    cast(product_id as bigint) as product_id,
    cast(balance as decimal(18, 2)) as source_balance,
    currency,
    cast(opening_date as date) as opened_on,
    cast(closed_date as date) as closed_on,
    status as account_status,
    cast(updated_at as timestamp) as updated_at,
    cast(_extract_date as date) as extract_date,
    cast(_loaded_at as timestamp) as loaded_at
from source