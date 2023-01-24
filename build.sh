# needs a ~/.dbt/profiles.yml file like the one here to point dbt to the DuckDB databae
export BASEDIR="/Users/myuserid/projects/MTA"
export DBFILE="mta.db"
export DATADIR="downloads"
export FLASK_APP="superset"

# export MAPBOX_API_KEY= see https://docs.mapbox.com/help/getting-started/access-tokens/
# export ENABLE_TEMPLATE_PROCESSING=True or set in superset's config.py

cd $BASEDIR/dbt_mta
dbt seed
dbt run
dbt test
