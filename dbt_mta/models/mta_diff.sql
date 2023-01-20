WITH mta_diff AS (
    SELECT 
        date, 
        date_time, 
        station, 
        turnstile,
        entry_counter - LAG(entry_counter) OVER (PARTITION BY station, turnstile ORDER BY date_TIME) AS entries,
        exit_counter - LAG(exit_counter) OVER (PARTITION BY station, turnstile ORDER BY date_TIME) AS exits,
    FROM {{ref('mta_staging')}})
select * from mta_diff
    where entries >= 0 and entries < 7200 and exits >= 0 and exits <7200
