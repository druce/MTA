select
    date_trunc('day', date_time) date,
    4 * floor(date_part('hour', DATE_TIME) / 4) as hour,
    dayname(date) dow,
    pretty_name station,
    latitude,
    longitude,
    borough,
    sum(entries) entries,
    sum(exits) exits,
from
    {{ref('mta_clean')}} mta_clean
group by
    date,
    hour,
    pretty_name,
    latitude,
    longitude,
    borough

{{ config(
  post_hook = "
    alter table station_hourly alter entries type int;
    alter table station_hourly alter exits type int;
    alter table station_hourly alter hour type int;
    update station_hourly set hour = 24 where hour = 0;
") }}
