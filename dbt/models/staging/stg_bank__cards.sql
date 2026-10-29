with source as (
    select * from {{ source('bank', 'cards') }}
)

select
    cast(card_id as bigint) as card_id,
    cast(account_id as bigint) as account_id,
    cast(product_id as bigint) as product_id,
    right(cast(card_number as varchar), 4) as card_last4,
    {{ pseudonymise('card_number') }} as card_number_hash,
    cast(expiry_date as varchar) as expiry_raw,
    last_day(cast(try_strptime(expiry_date, '%m/%y') as date)) as expires_on,
    cast(issue_date as date) as issued_on,
    status as card_status,
    cast(updated_at as timestamp) as updated_at,
    cast(_extract_date as date) as extract_date,
    cast(_loaded_at as timestamp) as loaded_at
from source
-- cvv is never selected: PCI DSS forbids storing it after authorisation
