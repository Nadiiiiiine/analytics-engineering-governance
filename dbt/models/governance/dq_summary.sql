-- Violations per rule for the current extract: the table behind the quality dashboard.

select
    rules.rule_id,
    rules.rule_name,
    rules.table_name,
    rules.severity,
    rules.action,
    count(violations.record_id) as violation_count
from {{ ref('dq_rules') }} as rules
left join {{ ref('dq_violations') }} as violations on rules.rule_id = violations.rule_id
group by all
order by rules.rule_id
