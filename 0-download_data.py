from datetime import date, timedelta
from time import strftime
from pathlib import Path
from os import system

downloaddir = "downloads"
prefix = "http://web.mta.info/developers/data/nyct/turnstile/turnstile_"
suffix = ".txt"
start_date = date(2019, 1, 7)  # start with 1st full week of 2019
end_date = date.today()
delta = end_date - start_date   # returns timedelta

alldays = [start_date + timedelta(days=i) for i in range(delta.days + 1)]
alldays = [day for day in alldays if day.weekday() == 5]

for d in alldays:
    infix = strftime("%y%m%d", d.timetuple())
    url = "%s%s%s" % (prefix, infix, suffix)
    src = "%s/%s%s" % (downloaddir, infix, suffix)

    if Path(src).is_file():
        continue

    cmd = "curl %s > %s" % (url, src)
    print(cmd)
    system(cmd)
