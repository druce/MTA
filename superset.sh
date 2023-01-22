#!/usr/bin/env bash

export FLASK_APP=superset
export MAPBOX_API_KEY=<mykey>
export ENABLE_TEMPLATE_PROCESSING=True
source /home/ubuntu/anaconda3/etc/profile.d/conda.sh
conda activate superset
# superset fab create-admin
superset run -h 0.0.0.0 -p 8088 --with-threads --reload --debugger
# add database, choose duckdb, duckdb:////home/ubuntu/mta.db
