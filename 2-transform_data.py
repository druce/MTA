# create mta_staging and mta_clean from mta_raw

from time import strftime
from os import path, getcwd, chdir
from pathlib import Path
import duckdb


def run_sql(query, verbose=False):
    # run_sql should accept parameters and let db handle them for safety
    global con
    if verbose:
        print(query)
    con.execute(query)
    return con.fetchall()


def log(s):
    global CURRENTFILE
    print("%s - %s - %s" % (strftime("%H:%M:%S"), CURRENTFILE, s))


CURRENTFILE = path.basename(__file__)
BASEDIR = Path(__file__).parent.resolve()
chdir(BASEDIR)
HARD_CUTOFF = 7200

log("Starting data load in %s" % getcwd())
log("Creating mta_raw table")

con = duckdb.connect('mta.db')

log("Creating mta_staging and deduplicating")
query = """
    create or replace table mta_staging as
    select distinct
        CONCAT("C/A" , ' ' , UNIT , ' ' , SCP) TURNSTILE,
        CONCAT(STATION, '-', LINENAME) STATION,
        DIVISION,
        "DATE",
        make_timestamp(date_part('year', DATE),
            date_part('month', DATE),
            date_part('day', DATE),
            date_part('hour', TIME),
            date_part('minute', TIME),
            date_part('second', TIME)) DATE_TIME,
        ENTRY_COUNTER,
        EXIT_COUNTER
    from mta_raw
    where "DESC" <> 'RECOVR AUD'
"""
run_sql(query)

result = run_sql('select count(*) from mta_staging')
log("Loaded   %d rows into mta_staging" % result[0][0])

log("Make combined station name from STATION, DIVISION")
query = """
update mta_staging
set station = concat(station, '-', division)
where division not in ('RIT', 'BMT', 'IRT', 'IND');
"""
run_sql(query)

log("Fix stations with more than 1 name")
fixes = {
    '14 ST-UNION SQ-LNQR456W': '14 ST-UNION SQ-456LNQRW',
    '161/YANKEE STAD-BD4': '161/YANKEE STAD-4BD',
    '34 ST-PENN STA-123': '34 ST-PENN STA-123ACE',
    '34 ST-PENN STA-ACE': '34 ST-PENN STA-123ACE',
    '42 ST-PORT AUTH-ACENGRS1237W': '42 ST-PORT AUTH-ACENQRS1237W',
    '59 ST-NQR456W': '59 ST-456NQRW',
    '59 ST-NRW': '59 ST-456NQRW',
    '59 ST COLUMBUS-ABCD1': '59 ST COLUMBUS-1ABCD',
    'ATL AV-BARCLAY-BDNQR2345': 'ATL AV-BARCLAY-2345BDNQR',
    'BOROUGH HALL-R2345': 'BOROUGH HALL-2345R',
    'COURT SQ-23 ST-EMG': 'COURT SQ-EMG',
    'FULTON ST-ACJZ2345': 'FULTON ST-2345ACJZ',
    'GUN HILL RD-5': 'GUN HILL RD-25',
    'PATH WTC 2-PTH-1': 'PATH NEW WTC-PTH-1',
    'PELHAM PKWY-5': 'PELHAM PKWY-25',
}
query = """
create or replace temp table station_name_map (
    STATION_SRC  VARCHAR,
    STATION_DEST VARCHAR);
"""
run_sql(query)

for k, v in fixes.items():
    log(f"{k} -> {v}")
    run_sql(f"insert into station_name_map values ('{k}', '{v}');")

query = """
update mta_staging
set station = (
    select station_dest from station_name_map
    where station_name_map.station_src = mta_staging.station
)
where station in (select station_src from station_name_map);
"""
run_sql(query)

log("Drop unused columns")
query = """
ALTER TABLE mta_staging DROP DIVISION;
"""
run_sql(query)

log("Create mta_clean and diff by turnstile")
query = """
CREATE OR REPLACE TABLE mta_clean AS
SELECT DATE, DATE_TIME, STATION, TURNSTILE,
ENTRY_COUNTER,
ENTRY_COUNTER - lag(ENTRY_COUNTER) OVER (PARTITION BY STATION, TURNSTILE ORDER BY DATE_TIME) AS ENTRIES,
2000 ENTRIES_CUTOFF,
EXIT_COUNTER,
EXIT_COUNTER - lag(EXIT_COUNTER) OVER (PARTITION BY STATION, TURNSTILE ORDER BY DATE_TIME) AS EXITS,
2000 EXITS_CUTOFF,
0 DELETE_MARKER
FROM mta_staging;
"""
run_sql(query)

result = run_sql('select count(*) from mta_clean')
log("Loaded   %d rows into mta_clean" % result[0][0])

# run_sql("drop table mta_staging;")

query = """
ALTER TABLE mta_clean drop column ENTRY_COUNTER;
ALTER TABLE mta_clean drop column EXIT_COUNTER;
"""
run_sql(query)

log("Delete NULLs (start of window with no diff)")
run_sql("delete from mta_clean where entries is null and exits is null;")

log("Delete negatives where turnstile counter got reset during maintenance")
run_sql("delete from mta_clean where ENTRIES < 0; delete from mta_clean where EXITS < 0;")

log("Delete entries or exits greater than hard limit of %d" % HARD_CUTOFF)
run_sql("delete from mta_clean where ENTRIES>%d; delete from mta_clean where EXITS>%d;" % (HARD_CUTOFF, HARD_CUTOFF))

result = run_sql('select count(*) from mta_clean')
log("Left     %d rows into mta_clean" % result[0][0])

log("Compute average, sd, observation count by turnstile")
query = """
create or replace table entry_avg as
select station, TURNSTILE, avg(entries) MEAN, stddev(entries) SD, count(*) N,
from mta_clean
where entries > 0
group by station, TURNSTILE;
"""
run_sql(query)
query = """
create or replace table exit_avg as
select station, TURNSTILE, avg(exits) MEAN, stddev(exits) SD, count(*) N,
from mta_clean
where exits > 0
group by station, TURNSTILE;
"""
run_sql(query)

log("Compute a cutoff by turnstile based on max(2000, mean+3SD where n>20)")
query = """
alter table entry_avg add column ENTRIES_CUTOFF DOUBLE;
update entry_avg set ENTRIES_CUTOFF = MEAN + 3 * SD;
update entry_avg set ENTRIES_CUTOFF = 2000 where N <= 20;
update entry_avg set ENTRIES_CUTOFF = 2000 where isnan(ENTRIES_CUTOFF);
update entry_avg set ENTRIES_CUTOFF = 2000 where ENTRIES_CUTOFF < 2000;
"""
run_sql(query)
query = """
alter table exit_avg add column EXITS_CUTOFF DOUBLE;
update exit_avg set EXITS_CUTOFF = MEAN + 3 * SD;
update exit_avg set EXITS_CUTOFF = 2000 where N <= 20;
update exit_avg set EXITS_CUTOFF = 2000 where isnan(EXITS_CUTOFF);
update exit_avg set EXITS_CUTOFF = 2000 where EXITS_CUTOFF < 2000;
"""
run_sql(query)

log("Update entries_cutoff in each row in mta_clean table")
query = """
update mta_clean
set ENTRIES_CUTOFF = (
select ENTRIES_CUTOFF from entry_avg
    where
    entry_avg.station = mta_clean.station and
    entry_avg.turnstile = mta_clean.turnstile
)
where exists (
    select 1 from entry_avg
    where
    entry_avg.station = mta_clean.station and
    entry_avg.turnstile = mta_clean.turnstile
)
"""
run_sql(query)
query = """
update mta_clean
set EXITS_CUTOFF = (
select EXITS_CUTOFF from exit_avg
    where
    exit_avg.station = mta_clean.station and
    exit_avg.turnstile = mta_clean.turnstile
)
where exists (
    select 1 from exit_avg
    where
    exit_avg.station = mta_clean.station and
    exit_avg.turnstile = mta_clean.turnstile
)
"""

log("Delete based on entries or exits > cutoff")
run_sql("delete from mta_clean where entries > entries_cutoff;")
run_sql("delete from mta_clean where exits > exits_cutoff;")

result = run_sql('select count(*) from mta_clean')
log("Left     %d rows into mta_clean" % result[0][0])

log("Delete where both entries and exits are 0")
query = "delete from mta_clean where entries = 0 and exits = 0;"
run_sql(query)

result = run_sql('select count(*) from mta_clean')
log("Left     %d rows into mta_clean" % result[0][0])

log("Finishing")

query = """
ALTER TABLE mta_clean drop column ENTRIES_CUTOFF;
ALTER TABLE mta_clean drop column EXITS_CUTOFF;
ALTER TABLE mta_clean drop column DELETE_MARKER;
"""
run_sql(query)

log("Finished data load")
