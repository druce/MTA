with stations as (
 select distinct station from {{ref('mta_diff')}}
 order by station
)
select
    stations.station,
    concat(map.stop_name, '-', map.daytime_routes, ' (', map.borough, ')') pretty_name,
    latitude,
    longitude,
    borough.borough_desc,
    -1 borough,
    map.cbd
from stations
    left outer join {{ref('station_map')}} map on stations.station=map.station
    left outer join {{ref('borough_map')}} borough on map.borough = borough.borough

{{ config(
  post_hook = "
    update station_list set borough_desc='Manhattan below 63 St' where cbd='Y';
    update station_list set borough_desc='Manhattan above 63 St' where borough_desc = 'Manhattan' and cbd='N';
    update station_list set borough = 1 where borough_desc='Manhattan below 63 St';
    update station_list set borough = 2 where borough_desc='Manhattan above 63 St';
    update station_list set borough = 3 where borough_desc='Brooklyn';
    update station_list set borough = 4 where borough_desc='Queens';
    update station_list set borough = 5 where borough_desc='Bronx';
") }}
