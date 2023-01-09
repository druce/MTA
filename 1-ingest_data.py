# load data from downloads into mta_raw table
from time import strftime
from os import path, listdir, getcwd, chdir
from pathlib import Path
import subprocess

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
DBFILE = "mta.db"
DATADIR = "downloads"
chdir(BASEDIR)

log("Starting data load in %s" % getcwd())
log("Loading into %s/%s" % (BASEDIR, DBFILE))
log("Creating mta_raw table")

con = duckdb.connect('mta.db')
query = """
create or replace table mta_raw(
    "C/A" VARCHAR,
    UNIT VARCHAR,
    SCP VARCHAR,
    STATION VARCHAR,
    LINENAME VARCHAR,
    DIVISION VARCHAR,
    DATE DATE,
    TIME TIME,
    "DESC" VARCHAR,
    ENTRY_COUNTER INTEGER,
    EXIT_COUNTER INTEGER);
"""
run_sql(query)

datafiles = sorted([DATADIR + "/" + f for f in listdir(DATADIR) if f[-4:] == ".txt"])

log("Found %d files in %s/%s" % (len(datafiles), getcwd(), DATADIR))

query = """
insert into mta_raw SELECT * FROM read_csv('%s', \
                                                 delim=',', \
                                                 header=True, \
                                                 columns={'C/A': 'VARCHAR', \
                                                          'UNIT': 'VARCHAR', \
                                                          'SCP': 'VARCHAR', \
                                                          'STATION': 'VARCHAR', \
                                                          'LINENAME': 'VARCHAR', \
                                                          'DIVISION': 'VARCHAR', \
                                                          'DATE': 'DATE', \
                                                          'TIME': 'TIME',\
                                                          'DESC': 'VARCHAR',\
                                                          'ENTRIES': 'INTEGER',\
                                                          'EXITS': 'INTEGER',},\
                                                      dateformat='%%m/%%d/%%Y');
"""
log("Ingesting")

for f in datafiles:
    log("Loading %s" % f)
    run_sql(query % f)

log("Verifying")
result = subprocess.run(['wc', '-l', ] + datafiles, stdout=subprocess.PIPE)
lastresult = result.stdout.splitlines()[-1]
# total lines - number of header rows
expected = int(lastresult.split()[0]) - len(datafiles)
log("Expected %d rows from 'wc'" % expected)
result = run_sql('select count(*) from mta_raw')
log("Loaded   %d rows into mta_raw" % result[0][0])
log("Ended data load from %s/%s" % (getcwd(), DATADIR))
