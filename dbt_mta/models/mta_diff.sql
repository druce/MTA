-- coompute abs diffs from mta_staging, drop anomalous entries or exits that are prob maintenance
with subquery as 
    (SELECT 
        date_time, 
        station, 
        turnstile,
        entry_counter,
        abs(entry_counter - LAG(entry_counter) OVER w) AS entries,
        exit_counter,
        abs(exit_counter - LAG(exit_counter) OVER w) AS exits,
        date_diff('second', LAG(date_time) OVER w, date_time) as seconds_diff,
        date_part('day', date_time - lag(date_time) over w) * 24 +
            date_part('hour', date_time - lag(date_time) over w) as hours_difference
    FROM {{ref('mta_staging')}}
    WINDOW w AS (PARTITION BY station, turnstile ORDER BY date_time)
    )
select * from subquery
    -- drop rows where we are seeing negative numbers or more than 1 click per second
    where 
    seconds_diff < 345600  -- after 24h, not attributing to correct date, clearly maintenance was performed
    and entries < (seconds_diff / 2) -- no more than 1 entry every 2 seconds
    and exits < (seconds_diff / 2)
    and entries < 7200 -- hard cap regardless of how long
    and exits < 7200
    -- typically max for a turnstile in a legit 4 hour period is like 2000-2500 
    -- sometimes a report is skipped, one row picks up multiple periods
    -- but at some point you're recording a lot of data in the wrong period or day even if real
    -- maybe less problematic to drop a row than to move many legit entries to wrong period


{# ignore this
-- chris whong calc - match numbers at https://www.subwayridership.nyc/
-- see https://github.com/qri-io/data-stories-scripts/tree/master/nyc-turnstile-counts

    {{ config(
    post_hook = "
        UPDATE mta_diff
        SET
            entries = CASE WHEN abs(entries) < 10000 THEN abs(entries) ELSE 0 END,
            exits = CASE WHEN abs(exits) < 10000 THEN abs(exits) ELSE 0 END;

        -- SET
        --     entries = CASE WHEN abs(entries) < 10000 AND hours_difference <= 24 THEN abs(entries) ELSE 0 END,
        --     exits = CASE WHEN abs(exits) < 10000 AND hours_difference <= 24 THEN abs(exits) ELSE 0 END;
    ") }}
    #}

