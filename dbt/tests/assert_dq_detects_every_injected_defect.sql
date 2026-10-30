-- The quality framework must find every defect the generator injected
-- (no false negative) and nothing else (no false positive).
-- Each returned row is a failure.

with expected as (
    select
        rule_id,
        cast(record_id as varchar) as record_id
    from {{ source('bank', 'defect_manifest') }}
),

detected as (
    select distinct
        rule_id,
        record_id
    from {{ ref('dq_violations') }}
)

select
    'missed' as issue,
    e.rule_id,
    e.record_id
from expected as e
left join detected as d on e.rule_id = d.rule_id and e.record_id = d.record_id
where d.rule_id is null

union all

select
    'false_positive' as issue,
    d.rule_id,
    d.record_id
from detected as d
left join expected as e on d.rule_id = e.rule_id and d.record_id = e.record_id
where e.rule_id is null
