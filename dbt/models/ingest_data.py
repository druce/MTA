# load data from downloads into mta.mta_raw table
from time import strftime
import os
import subprocess

import pandas as pd
import duckdb

BASEDIR = os.getenv('BASEDIR')
if not BASEDIR:
    print("BASEDIR environment variable not defined, exiting")
    exit(1)
CURRENTFILE = os.path.basename(__file__)
DOWNLOADDIR = os.getenv('DATADIR')
DATADIR = "%s/%s" % (BASEDIR, DOWNLOADDIR)
DBFILE = os.getenv('DBFILE')
con = duckdb.connect("%s/%s" % (BASEDIR, DBFILE))


def model(dbt, session):

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

    os.chdir(BASEDIR)

    log("Starting data ingestion in %s" % os.getcwd())
    log("Ingesting from %s into %s/%s" % (DATADIR, BASEDIR, DBFILE))
    log("Creating mta.mta_raw table")

    query = """CREATE SCHEMA IF NOT EXISTS mta"""
    run_sql(query)

    query = """
    create or replace table mta.mta_raw(
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

    datafiles = sorted([DATADIR + "/" + f for f in os.listdir(DATADIR) if f[-4:] == ".txt"])

    log("Found %d files in %s/%s" % (len(datafiles), os.getcwd(), DATADIR))

    query = """
    insert into mta.mta_raw SELECT * FROM read_csv('%s', \
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

    for f in datafiles:
        log("Ingesting %s" % f)
        run_sql(query % f)

    log("Verifying row count")
    result = subprocess.run(['wc', '-l', ] + datafiles, stdout=subprocess.PIPE)
    lastresult = result.stdout.splitlines()[-1]
    # total lines - number of header rows
    expected = int(lastresult.split()[0]) - len(datafiles)
    log("Expected %d rows from 'wc'" % expected)
    result = run_sql('select count(*) from mta.mta_raw')
    log("Loaded   %d rows into mta.mta_raw" % result[0][0])
    log("Ended data ingestion from %s/%s" % (BASEDIR, DATADIR))

    final_df = pd.DataFrame({'rows': [result[0][0]]})

    return final_df
