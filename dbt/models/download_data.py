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

    BASEDIR = os.getenv('BASEDIR')
    if not BASEDIR:
        print("BASEDIR environment variable not defined, exiting")
        exit(1)
    DOWNLOADDIR = os.getenv('DATADIR')
    DATADIR = "%s/%s" % (BASEDIR, DOWNLOADDIR)
    PREFIX = "http://web.mta.info/developers/data/nyct/turnstile/turnstile_"
    SUFFIX = ".txt"
    START_DATE = date(2019, 1, 7)  # start with 1st full week of 2019
    END_DATE = date.today()

    os.chdir(BASEDIR)

    delta = END_DATE - START_DATE   # returns timedelta
    alldays = [START_DATE + timedelta(days=i) for i in range(delta.days + 1)]
    alldays = [day for day in alldays if day.weekday() == 5]

    for d in alldays:
        infix = strftime("%y%m%d", d.timetuple())
        url = "%s%s%s" % (PREFIX, infix, SUFFIX)
        src = "%s/%s%s" % (DATADIR, infix, SUFFIX)

        if Path(src).is_file():
            continue

        cmd = "curl %s > %s" % (url, src)
        print(cmd)
        os.system(cmd)

    datafiles = sorted([DATADIR + "/" + f for f in os.listdir(DATADIR) if f[-4:] == ".txt"])
    result = subprocess.run(['wc', '-l', ] + datafiles, stdout=subprocess.PIPE)
    lastresult = result.stdout.splitlines()[-1]
    # total lines - number of header rows
    expected = int(lastresult.split()[0]) - len(datafiles)
    final_df = pd.DataFrame({'rows': [expected]})

    return final_df
