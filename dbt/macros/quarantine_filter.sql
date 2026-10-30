{#- Keep only the rows no quarantine rule has flagged for this table. -#}
{% macro quarantine_filter(table_name, id_column) -%}
    {{ id_column }} not in (
        select cast(record_id as bigint)
        from {{ ref('dq_violations') }}
        where table_name = '{{ table_name }}'
            and action = 'quarantine'
    )
{%- endmacro %}