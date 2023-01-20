# needs stuff installed in dbt dockerfile (don't need to run in docker)
# needs a ~/.dbt/profiles.yml file like the one here to point dbt to the DuckDB databae
export BASEDIR="/Users/drucev/projects/MTA"
export DBFILE="mta.db"
export DATADIR="downloads"

# export MAPBOX_API_KEY= see https://docs.mapbox.com/help/getting-started/access-tokens/
# export ENABLE_TEMPLATE_PROCESSING=True or set in superset's config.py

cd $BASEDIR/dbt_mta
dbt seed
dbt run
dbt test
