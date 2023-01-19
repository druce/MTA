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
            CONCAT(
                COALESCE(slo.STATION_DEST, CONCAT(STATION, '-', LINENAME)), 
                COALESCE(dlo.division_dest, '')
                ) STATION,
            ENTRY_COUNTER,
            EXIT_COUNTER
        from {{ source('mta', 'mta_raw') }}
        left outer join {{ref('station_label_override')}} slo
        on slo.station_src = CONCAT(STATION, '-', LINENAME)
        left outer join {{ref('division_label_override')}} dlo
        on dlo.division_src = division
        where "DESC" <> 'RECOVR AUD'
        and division not in ('SRT')
        and station not in ('CITY / BUS','EXCHANGE PLACE','GROVE STREET','HARRISON','JOURNAL SQUARE','LACKAWANNA','NEWARK BM BW','NEWARK C','NEWARK HM HE','NEWARK HW BMEBE','PAVONIA/NEWPORT')
        and date_part('year', DATE) > 2018
    )

select * from final
