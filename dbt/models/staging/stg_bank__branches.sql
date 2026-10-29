with source as (
    select * from {{ source('bank', 'branches') }}
)

select
    cast(branch_id as bigint) as branch_id,
    branch_name,
    city,
    cast(postcode as varchar) as postcode,
    cast(opening_date as date) as opened_on,
    cast(_loaded_at as timestamp) as loaded_at
from source