with final as (

    select distinct
        make_timestamp(date_part('year', DATE),
            date_part('month', DATE),
            date_part('day', DATE),
            date_part('hour', TIME),
            date_part('minute', TIME),
            date_part('second', TIME)) DATE_TIME,
        "DATE",
        CONCAT("C/A" , ' ' , UNIT , ' ' , SCP) TURNSTILE,
        CONCAT(STATION, '-', LINENAME) STATION,
        DIVISION,
        ENTRY_COUNTER,
        EXIT_COUNTER
    from mta_raw
    where "DESC" <> 'RECOVR AUD'
)

select * from final

{{ config(
  post_hook = "update dbt_dv.mta_staging
    set station = (
      select station_dest from {{ref('station_label_override')}}
      where station_src = station
    )
    where station in (select station_src from {{ref('station_label_override')}})
"
) }}

{{ config(
    post_hook = "update dbt_dv.mta_staging
        set station = concat(station, '-', division)
        where division not in ('RIT', 'BMT', 'IRT', 'IND')
    "
) }}

