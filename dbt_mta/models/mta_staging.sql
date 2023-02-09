-- move from mta_raw to mta_staging
select distinct
    make_timestamp(date_part('year', DATE),
        date_part('month', DATE),
        date_part('day', DATE),
        date_part('hour', TIME),
        date_part('minute', TIME),
        date_part('second', TIME)) DATE_TIME,
    CONCAT("C/A" , ' ' , UNIT , ' ' , SCP) TURNSTILE,
    CONCAT(
        COALESCE(slo.STATION_DEST, CONCAT(STATION, '-', LINENAME)), 
        COALESCE(dlo.division_dest, '')
        ) STATION,
    ENTRY_COUNTER,
    EXIT_COUNTER
from 
    {{ source('mta', 'mta_raw') }} mta_raw
    -- might be more consistent to just use the complex
    -- first cut I didn't have complex, merged stations that needed merging using station_level_override
    -- for some complexes like 624 cortlandt/chambers/park place/wtc, 53/51st information is lost
    -- I usually merged less if no ambiguity
    left outer join {{ref('station_label_override')}} slo on slo.station_src = CONCAT(STATION, '-', LINENAME)
    -- just wanted more legible station ID
    left outer join {{ref('division_label_override')}} dlo on dlo.division_src = division
    -- where "DESC" <> 'RECOVR AUD'
    -- skip staten island, only 2 stations reflected in CSVs for some reason
where
    division not in ('SRT')
    -- skip NJ PATH stations but keep NYC
    and mta_raw.station not in ('CITY / BUS','EXCHANGE PLACE','GROVE STREET','HARRISON','JOURNAL SQUARE','LACKAWANNA','NEWARK BM BW','NEWARK C','NEWARK HM HE','NEWARK HW BMEBE','PAVONIA/NEWPORT')
    -- start 1/1/2019
    and date_part('year', DATE) > 2018

-- check a week with no recovr aud or weirdness, match exactly
-- clone repo, grep recovr aud
-- find logic with the dropping records, dupe exactly
