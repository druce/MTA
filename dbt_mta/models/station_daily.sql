select
    date_trunc('day', date_time) date,
    pretty_name station,
    latitude,
    longitude,
    borough,
    dayname(date) dow,
    dayname(date) in ('Saturday', 'Sunday') is_weekend,
    sum(entries) entries,
    sum(exits) exits,
from
    {{ref('mta_clean')}} mta_clean
group by
    date,
    pretty_name,
    latitude,
    longitude,
    borough

{{ config(
  post_hook = "
    alter table station_daily alter entries type int;
    alter table station_daily alter exits type int;
") }}
