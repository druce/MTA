WITH exit_avg AS (
    select station, turnstile, avg(exits) mean, stddev(exits) sd, count(*) n, avg(exits)+4*stddev(exits) exits_cutoff 
    from {{ref('mta_diff')}}
    where exits > 0
    group by station, turnstile)
select * from exit_avg

{{ config(
    post_hook = "
        update dbt_dv.exit_avg set exits_cutoff = 2000 where N <= 20;
        update dbt_dv.exit_avg set exits_cutoff = 2000 where isnan(exits_cutoff);
        update dbt_dv.exit_avg set exits_cutoff = 2000 where exits_cutoff < 2000;
    "
) }}

