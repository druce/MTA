# needs stuff installed in dbt dockerfile (don't need to run in docker)
# needs a ~/.dbt/profiles.yml file like the one here to point dbt to the DuckDB databae
export BASEDIR="/Users/drucev/projects/MTA"
export DBFILE="mta.db"
export DATADIR="downloads"

cd $BASEDIR/dbt
dbt seed
dbt run
