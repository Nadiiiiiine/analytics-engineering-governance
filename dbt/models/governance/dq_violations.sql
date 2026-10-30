with transactions as (
    select * from {{ ref('stg_bank__transactions') }}
),

accounts as (
    select * from {{ ref('stg_bank__accounts') }}
),

customers as (
    select * from {{ ref('stg_bank__customers') }}
),

account_totals as (
    -- duplicates removed, every received transaction counted, whatever its date
    select
        account_id,
        sum(amount) as total_amount
    from (select distinct transaction_id, account_id, amount from transactions)
    group by account_id
),

checks as (

    -- DQ01: the same transaction delivered more than once
    select
        'DQ01' as rule_id,
        transaction_id as record_id
    from transactions
    group by transaction_id
    having count(*) > 1

    union all

    -- DQ02: the direction label contradicts the sign of the amount
    select distinct
        'DQ02' as rule_id,
        transaction_id as record_id
    from transactions
    where
        (direction = 'credit' and amount < 0)
        or (direction = 'debit' and amount > 0)

    union all

    -- DQ03: transaction on an account that does not exist
    select distinct
        'DQ03' as rule_id,
        t.transaction_id as record_id
    from transactions as t
    left join accounts as a on t.account_id = a.account_id
    where a.account_id is null

    union all

    -- DQ04: transaction dated before its account opened
    select distinct
        'DQ04' as rule_id,
        t.transaction_id as record_id
    from transactions as t
    inner join accounts as a on t.account_id = a.account_id
    where t.transaction_date < a.opened_on

    union all

    -- DQ05: transaction dated after the extract date
    select distinct
        'DQ05' as rule_id,
        transaction_id as record_id
    from transactions
    where transaction_date > extract_date

    union all

    -- DQ06: malformed email
    select
        'DQ06' as rule_id,
        customer_id as record_id
    from customers
    where not is_email_valid

    union all

    -- DQ07: postcode missing from the reference
    select
        'DQ07' as rule_id,
        c.customer_id as record_id
    from customers as c
    left join {{ ref('reference_postcodes') }} as p on c.postcode = p.postcode
    where p.postcode is null

    union all

    -- DQ08: balance differs by at least one cent from its deduplicated transactions
    select
        'DQ08' as rule_id,
        a.account_id as record_id
    from accounts as a
    left join account_totals as t on a.account_id = t.account_id
    where abs(a.source_balance - coalesce(t.total_amount, 0)) >= 0.01

    union all

    -- DQ09: loan ending before it starts
    select
        'DQ09' as rule_id,
        loan_id as record_id
    from {{ ref('stg_bank__loans') }}
    where end_date < start_date

    union all

    -- DQ10: card expiry that cannot be parsed as MM/YY
    select
        'DQ10' as rule_id,
        card_id as record_id
    from {{ ref('stg_bank__cards') }}
    where expires_on is null

)

select
    checks.rule_id,
    rules.rule_name,
    rules.table_name,
    rules.severity,
    rules.action,
    cast(checks.record_id as varchar) as record_id,
    (select max(extract_date) from transactions) as extract_date
from checks
inner join {{ ref('dq_rules') }} as rules on checks.rule_id = rules.rule_id
