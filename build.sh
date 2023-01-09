export BASEDIR="/Users/drucev/projects/MTA"
export DBFILE="mta.db"
export DATADIR="downloads"

cd $BASEDIR/dbt
dbt seed
dbt run
