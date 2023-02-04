#!/usr/bin/bash

# needs a ~/.dbt/profiles.yml file like the one here to point dbt to the DuckDB databae
export HOMEDIR="/home/myuserid"
export BASEDIR="$HOMEDIR/projects/MTA"
export DBFILE="mta.db"
export DATADIR="downloads"
export FLASK_APP="superset"

date
# activate environment
source $HOMEDIR/anaconda3/etc/profile.d/conda.sh
conda activate dbt

# export MAPBOX_API_KEY= see https://docs.mapbox.com/help/getting-started/access-tokens/
# export ENABLE_TEMPLATE_PROCESSING=True doesn't work, edit in superset's config.py

# stop anything that is using mta.db (superset or plotlydash)
# put appropriate commands in wrapper.c and setuid on executable to run with root privileges
# $BASEDIR/suid_stop_plotlydash

cd $BASEDIR/dbt_mta
dbt seed
dbt run
dbt test

# $BASEDIR/suid_start_plotlydash

date
