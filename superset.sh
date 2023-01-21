#!/usr/bin/env bash

export FLASK_APP=superset
# https://docs.mapbox.com/help/getting-started/access-tokens/
export MAPBOX_API_KEY=<mykey>

export ENABLE_TEMPLATE_PROCESSING=True
# override didn't work, not sure how to set this option from command line, had to do
# vi ~/anaconda3/envs/superset/lib/python3.8/site-packages/superset/config.py
#     "ENABLE_TEMPLATE_PROCESSING": True,

conda activate superset
# set up user
# superset fab create-admin
superset run -h 0.0.0.0 -p 8088 --with-threads --reload --debugger
# add database, choose duckdb, duckdb:////home/ubuntu/mta.db
# import dashboard_export.zip
