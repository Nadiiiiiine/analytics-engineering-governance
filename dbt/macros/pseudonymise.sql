{#- Salted SHA-256 of a value. Same input + same salt = same hash, so the
    column still works as a join or deduplication key, but the original
    value cannot be read back. Set PII_SALT outside the repository. -#}
{% macro pseudonymise(expression) -%}
    sha256(concat('{{ env_var("PII_SALT", "local-dev-salt") }}', cast({{ expression }} as varchar)))
{%- endmacro %}