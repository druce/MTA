select
    date_time,
    mta_diff.station,
    concat(map.stop_name, '-', map.daytime_routes, ' (', map.borough, ')') pretty_name,
    mta_diff.turnstile,
    entries,
    exits,
    latitude,
    longitude,
    borough_desc borough,
    map.cbd,
    entry_avg.entries_cutoff,
    exit_avg.exits_cutoff
from
    {{ref('mta_diff')}} mta_diff
    left outer join {{ref('entry_avg')}} entry_avg on mta_diff.station=entry_avg.station and mta_diff.turnstile=entry_avg.turnstile
    left outer join {{ref('exit_avg')}} exit_avg on mta_diff.station=exit_avg.station and mta_diff.turnstile=exit_avg.turnstile
    left outer join {{ref('station_map')}} map on mta_diff.station=map.station
    left outer join {{ref('borough_map')}} borough on map.borough = borough.borough

{{ config(
  post_hook = "
    update mta_clean set entries_cutoff = 2000 where entries_cutoff is null;
    update mta_clean set exits_cutoff = 2000 where exits_cutoff is null;
    -- delete from mta_clean where entries > entries_cutoff;
    -- delete from mta_clean where exits > exits_cutoff;
    update mta_clean set pretty_name = station where pretty_name='- ()';
    alter table mta_clean alter entries type integer;
    alter table mta_clean alter exits type integer;
    update mta_clean set borough=concat('Manhattan below 63 St') where borough = 'Manhattan' and cbd='Y';
    update mta_clean set borough=concat('Manhattan above 63 St') where borough = 'Manhattan' and cbd='N';
") }}

{# should probably not do post_hook update, add another model with a filter and a formula #}
