from datetime import date, timedelta
from time import strftime
from pathlib import Path
import os
import subprocess
import pandas as pd

#######################################################
# Download data from MTA
#######################################################


def model(dbt, session):

    print("%s - Starting download" % (strftime("%H:%M:%S")))
    dbt.config(materialized="table")
    # read from env variables, should probably get from config.yml instead
    BASEDIR = os.getenv('BASEDIR')
    if not BASEDIR:
        print("%s - BASEDIR environment variable not defined, exiting" % strftime("%H:%M:%S"))
        exit(1)
    DOWNLOADDIR = os.getenv('DATADIR')
    DATADIR = "%s/%s" % (BASEDIR, DOWNLOADDIR)
    PREFIX = "http://web.mta.info/developers/data/nyct/turnstile/turnstile_"
    SUFFIX = ".txt"
    START_DATE = date(2019, 1, 1)
    END_DATE = date.today()

    os.chdir(BASEDIR)

    delta = END_DATE - START_DATE   # returns timedelta
    alldays = [START_DATE + timedelta(days=i) for i in range(delta.days + 1)]
    alldays = [day for day in alldays if day.weekday() == 5]

    count = 0
    for d in alldays:
        infix = strftime("%y%m%d", d.timetuple())
        url = "%s%s%s" % (PREFIX, infix, SUFFIX)
        src = "%s/%s%s" % (DATADIR, infix, SUFFIX)

        if Path(src).is_file():
            continue

        cmd = "curl %s > %s" % (url, src)
        print("%s - %s" % (strftime("%H:%M:%S"), cmd))
        os.system(cmd)
        count += 1

    print("%s - %d files downloaded" % (strftime("%H:%M:%S"), count))
    datafiles = sorted([DATADIR + "/" + f for f in os.listdir(DATADIR) if f[-4:] == ".txt"])
    result = subprocess.run(['wc', '-l', ] + datafiles, stdout=subprocess.PIPE)
    lastresult = result.stdout.splitlines()[-1]
    # total lines - number of header rows
    expected = int(lastresult.split()[0]) - len(datafiles)
    final_df = pd.DataFrame({'rows': [expected]})
    print("%s - %d files, %d rows in %s " % (strftime("%H:%M:%S"), len(datafiles), expected, DATADIR))
    print("%s - Finished download" % (strftime("%H:%M:%S")))

    return final_df
