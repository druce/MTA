-- coompute diffs from mta_staging, drop anomalous entries or exits that are prob maintenance
-- see https://github.com/qri-io/data-stories-scripts/tree/master/nyc-turnstile-counts
    SELECT 
        date_time, 
        station, 
        turnstile,
        entry_counter,
        entry_counter - LAG(entry_counter) OVER w AS entries,
        exit_counter,
        exit_counter - LAG(exit_counter) OVER w AS exits,
        date_diff('second', LAG(date_time) OVER w, date_time) as seconds_diff,
        date_part('day', date_time - lag(date_time) over w) * 24 +
            date_part('hour', date_time - lag(date_time) over w) as hours_difference
    FROM {{ref('mta_staging')}}
    WINDOW w AS (PARTITION BY station, turnstile ORDER BY date_time)

-- chris whong calc
{{ config(
  post_hook = "
    UPDATE mta_diff
    SET
        entries = CASE WHEN abs(entries) < 10000 AND hours_difference <= 24 THEN abs(entries) ELSE 0 END,
        exits = CASE WHEN abs(exits) < 10000 AND hours_difference <= 24 THEN abs(exits) ELSE 0 END;
") }}

-- select * from mta_diff
    -- drop rows where we are seeing negative numbers or more than 1 click per second
    -- where 
    -- time_diff < 345600  -- after 24h, not attributing to correct date, clearly maintenance was performed
    -- and entries >= 0
    -- and entries < (time_diff / 2) -- no more than 1 entry every 2 seconds
    -- and entries < 7200 -- hard cap regardless of how long
    -- typically max in a legit 4 hour period is like 2000-2500 
    -- sometimes report is skipped, one row picks up multiple periods
    -- but at some point you're moving a lot of data into the wrong period or day
    -- may be less problematic to drop a row than to move many legit entries to wrong period
    -- and exits >= 0
    -- and exits < (time_diff / 2)
    -- and exits < 7200

