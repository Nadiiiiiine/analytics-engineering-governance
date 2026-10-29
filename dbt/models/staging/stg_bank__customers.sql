with source as (
    select * from {{ source('bank', 'customers') }}
)

select
    cast(customer_id as bigint) as customer_id,
    {{ pseudonymise('lower(trim(email))') }} as email_hash,
    nullif(regexp_extract(lower(email), '@(.+)$', 1), '') as email_domain,
    regexp_full_match(lower(trim(email)), '[a-z0-9._-]+@[a-z0-9.-]+\.[a-z]{2,}') as is_email_valid,
    year(cast(dob as date)) as birth_year,
    cast(postcode as varchar) as postcode,
    city,
    cast(branch_id as bigint) as home_branch_id,
    cast(registration_date as date) as registered_on,
    cast(updated_at as timestamp) as updated_at,
    cast(_extract_date as date) as extract_date,
    cast(_loaded_at as timestamp) as loaded_at
from source
-- first_name, last_name, phone and the full date of birth 
