select
    date,
    station,
    pretty_name,
    latitude,
    longitude,
    cbd,
    dayname(date) dow,
    dayname(date) in ('Saturday', 'Sunday') is_weekend,
    sum(entries) entries,
    sum(exits) exits,
from
    {{ref('mta_clean')}} mta_clean
group by
    date,
    station,
    pretty_name,
    latitude,
    longitude,
    cbd
