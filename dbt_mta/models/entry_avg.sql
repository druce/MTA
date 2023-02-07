-- not used, could drop rows based on > 4 standard deviations from mean or 2000, whichever is greater
    select 
        station, 
        turnstile, 
        avg(entries) mean, 
        stddev(entries) sd, 
        count(*) n, 
        avg(entries)+4*stddev(entries) entries_cutoff 
    from {{ref('mta_diff')}}
    where entries > 0
    group by station, turnstile

{{ config(
    post_hook = "
        update entry_avg set ENTRIES_CUTOFF = 2000 where N <= 20;
        update entry_avg set ENTRIES_CUTOFF = 2000 where isnan(ENTRIES_CUTOFF);
        update entry_avg set ENTRIES_CUTOFF = 2000 where ENTRIES_CUTOFF < 2000;
    "
) }}

