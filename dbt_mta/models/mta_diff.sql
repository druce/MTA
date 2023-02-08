-- coompute diffs from mta_staging, drop anomalous entries or exits that are prob maintenance
WITH mta_diff AS (
    SELECT 
        date_time, 
        station, 
        turnstile,
        entry_counter - LAG(entry_counter) OVER (PARTITION BY station, turnstile ORDER BY date_time) AS entries,
        exit_counter - LAG(exit_counter) OVER (PARTITION BY station, turnstile ORDER BY date_time) AS exits,
        date_diff('second', LAG(date_time) OVER (PARTITION BY station, turnstile ORDER BY date_time), date_time) as time_diff
    FROM {{ref('mta_staging')}})
select * from mta_diff
    -- drop rows where we are seeing negative numbers or more than 1 click per second
    where 
    time_diff < 345600  -- after 24h, not attributing to correct date, clearly maintenance was performed
    and entries >= 0
    and entries < (time_diff / 2) -- no more than 1 entry every 2 seconds
    and entries < 10000 -- hard cap regardless of how long
    and exits >= 0
    and exits < (time_diff / 2)
    and exits < 10000