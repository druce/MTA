select
    -- split into date and integer hour
    date_trunc('day', date_time) date,
    -- truncate hour down to nearest multiple of 4
    4 * floor(date_part('hour', date_time) / 4) as hour,
    -- pretty name, borough from station_list
    map.pretty_name station,
    map.borough boro,
    sum(entries) entries,
    sum(exits) exits
from
    {{ref('mta_diff')}} mta_diff
    left outer join {{ref('station_list')}} map on mta_diff.station=map.station
group by 
    date,
    hour,
    map.pretty_name,
    boro
-- drop periods with no exits or entries
having sum(mta_diff.entries) > 0 or sum(mta_diff.exits) > 0

{{ config(
  post_hook = "
    alter table mta_clean alter hour type integer;
    alter table mta_clean alter entries type integer;
    alter table mta_clean alter exits type integer;
    -- move midnight to prev day, hour=24
    update mta_clean set hour=24, date=date-1 where hour = 0;
    delete from mta_clean where date_part('year', date)<2019;
") }}

{# ignore this
{{ config(
  post_hook = "
    update mta_clean set entries_cutoff = 2000 where entries_cutoff is null;
    update mta_clean set exits_cutoff = 2000 where exits_cutoff is null;
    -- delete from mta_clean where entries > entries_cutoff;
    -- delete from mta_clean where exits > exits_cutoff;
    update mta_clean set pretty_name = station where pretty_name='- ()';
    alter table mta_clean alter entries type integer;
    alter table mta_clean alter exits type integer;
") }}
#}