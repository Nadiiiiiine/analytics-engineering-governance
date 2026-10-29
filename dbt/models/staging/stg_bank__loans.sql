with source as (
    select * from {{ source('bank', 'loans') }}
)

select
    cast(loan_id as bigint) as loan_id,
    cast(customer_id as bigint) as customer_id,
    cast(branch_id as bigint) as branch_id,
    cast(product_id as bigint) as product_id,
    cast(principal_amount as decimal(18, 2)) as principal_amount,
    cast(interest_rate as decimal(5, 2)) as interest_rate,
    cast(term_months as integer) as term_months,
    cast(start_date as date) as start_date,
    cast(end_date as date) as end_date,
    status as loan_status,
    cast(updated_at as timestamp) as updated_at,
    cast(_extract_date as date) as extract_date,
    cast(_loaded_at as timestamp) as loaded_at
from source