WITH entry_avg AS (
    select station, turnstile, avg(entries) mean, stddev(entries) sd, count(*) n, avg(entries)+4*stddev(entries) entries_cutoff 
    from {{ref('mta_diff')}}
    where entries > 0
    group by station, turnstile)
select * from entry_avg

{{ config(
    post_hook = "
        update dbt_dv.entry_avg set ENTRIES_CUTOFF = 2000 where N <= 20;
        update dbt_dv.entry_avg set ENTRIES_CUTOFF = 2000 where isnan(ENTRIES_CUTOFF);
        update dbt_dv.entry_avg set ENTRIES_CUTOFF = 2000 where ENTRIES_CUTOFF < 2000;
    "
) }}

