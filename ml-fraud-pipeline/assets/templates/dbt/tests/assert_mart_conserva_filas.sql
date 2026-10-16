-- El mart no puede perder ni duplicar operaciones respecto al staging.
select 1
where (select count(*) from {{ ref('stg_datos') }}) <> (select count(*) from {{ ref('mart_features') }})
