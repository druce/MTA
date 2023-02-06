import os
from time import strftime
from datetime import date, datetime

from collections import defaultdict
from six import string_types
from copy import deepcopy

import pandas as pd

# db stuff
import sqlalchemy
from jinjasql import JinjaSql

# plotly
import plotly
import plotly.express as px
from dash import Dash, html, dcc, dash_table
import dash_bootstrap_components as dbc
from dash.dash_table import FormatTemplate
from dash.dash_table.Format import Format, Scheme
from dash.dependencies import Input, Output

from dotenv import load_dotenv

load_dotenv()
mapbox_token = os.getenv('MAPBOX_TOKEN')

DATADIR = os.getenv('DATADIR')
if not DATADIR:
    print("%s - DATADIR environment variable not defined, exiting" % strftime("%H:%M:%S"))
    exit(1)
DATAFILE = os.getenv('DATAFILE')
DATAPATH = "%s/%s" % (DATADIR, DATAFILE)

connection_string = 'duckdb:////%s' % DATAPATH
# print(connection_string)
con = sqlalchemy.create_engine(connection_string, connect_args={'read_only': True})

# print sql queries
verbosity = 0

############################################################
# queries to return dataframes for dashboard
############################################################


def quote_sql_string(value):
    '''
    If `value` is a string type, escapes single quotes in the string
    and returns the string enclosed in single quotes.
    else if value is a list, map quote_sql_string to each item in list
    else return value unchanged
    '''
    if isinstance(value, string_types):
        new_value = str(value)
        new_value = new_value.replace("'", "''")
        new_value = "'{}'".format(new_value)
        return new_value
    elif isinstance(value, list):
        return [quote_sql_string(v) for v in value]
    return value


def get_sql_from_template(con, query, bind_params=None, verbose=False):
    """
    Run Jinja template query against con, substituting bind_params
    """
    if not bind_params:
        if verbose:
            print(query)
        return pd.read_sql(query, con)

    # process bind_params
    if verbose:
        # copy and escape params for legibility
        params = deepcopy(bind_params)
        for key, val in params.items():
            params[key] = quote_sql_string(val)
        query_str, query_vals = JinjaSql().prepare_query(query, params)
        print(query_str % tuple(query_vals))

    # process params using ? style, run query, return dataframe
    query_str, query_vals = JinjaSql(param_style='qmark').prepare_query(query, bind_params)
    return pd.read_sql(query_str, con, params=query_vals)


def stations_fn(con, verbose=False):
    "return stations for dropdown"
    df = get_sql_from_template(con, "select distinct pretty_name from station_list order by pretty_name;", verbose)
    return df['pretty_name'].to_list()


def create_filter_current(con, filters, verbose=False):
    """make temp table filter_current from filters (just filter, no group by)"""

    query = """
    create or replace temp table filter_current as
    select
        date,
        datepart('dow', date) dow,
        hour,
        station,
        boro,
        entries,
        exits
    from
        mta_clean
    where
        TRUE
        {% if startdate %} and date >= {{startdate}} {% endif %}
        {% if enddate %} and date < {{enddate}} {% endif %}
        {% if dow %} and date_part('dow', date) in {{ dow | inclause }}  {% endif %}
        {% if tod %} and hour in {{ tod | inclause }} {% endif %}
        {% if boro %} and boro in {{ boro | inclause }} {% endif %}
        {% if sta %} and station in {{ sta | inclause }} {% endif %}
    """

    return get_sql_from_template(con, query, filters, verbose)


def create_filter_2019(con, filters, verbose=False):
    """make temp table filter_2019 from filters (just filter, no group by)"""

    query = """
    create or replace temp table filter_2019 as
    select
        date,
        datepart('dow', date) dow,
        hour,
        station,
        boro,
        entries,
        exits
    from
        mta_clean
    where
        date_part('year', DATE)=2019
        {% if dow %} and date_part('dow', date) in {{ dow | inclause }}  {% endif %}
        {% if tod %} and hour in {{ tod | inclause }} {% endif %}
        {% if boro %} and boro in {{ boro | inclause }} {% endif %}
        {% if sta %} and station in {{ sta | inclause }} {% endif %}
    """

    return get_sql_from_template(con, query, filters, verbose)


def create_filter_pandemic(con, filters, verbose=False):
    """make temp table filter_pandemic from filters (just filter, no group by)"""

    query = """
    create or replace temp table filter_pandemic as
    select
        date,
        datepart('dow', date) dow,
        hour,
        station,
        boro,
        entries,
        exits
    from
        mta_clean
    where
        date >= '2020-04-01' and date < '2021-04-01'
        {% if dow %} and date_part('dow', date) in {{ dow | inclause }}  {% endif %}
        {% if tod %} and hour in {{ tod | inclause }} {% endif %}
        {% if boro %} and boro in {{ boro | inclause }} {% endif %}
        {% if sta %} and station in {{ sta | inclause }} {% endif %}
    """

    return get_sql_from_template(con, query, filters, verbose)


def agg_station(con, source, verbose=False):
    """make temp table %source%_daily, group by station, aggregate by day"""
    query = """
    create or replace temp table {source}_daily as
    select
        date,
        dow,
        station,
        boro,
        sum(entries) entries,
        sum(exits) exits
    from
        {source}
    group by
        date,
        dow,
        station,
        boro,
    """.format(source=source)

    return get_sql_from_template(con, query, None, verbose)


def create_filter_current_daily(con, verbose=False):
    """make temp table filter_current_daily, group by station, aggregate by day"""
    return agg_station(con, "filter_current", verbose=verbose)


def create_filter_2019_daily(con, verbose=False):
    """make temp table filter_2019_daily, group by station, aggregate by day"""
    return agg_station(con, "filter_2019", verbose=verbose)


def create_filter_pandemic_daily(con, verbose=False):
    """make temp table filter_current_daily, group by station, aggregate by day"""
    return agg_station(con, "filter_pandemic", verbose=verbose)


def agg_summary(con, source, verbose=False):
    """make temp table %source%_summary, aggregate by date (all stations)"""

    query = """
    create or replace temp table {source}_summary as
    select
        date,
        dow,
        sum(entries) entries,
        sum(exits) exits
    from
        {source}_daily
    group by
        date,
        dow,
    """.format(source=source)

    return get_sql_from_template(con, query, None, verbose)


def create_filter_current_summary(con, verbose=False):
    """make temp table filter_current_day, group by station, aggregate by day"""
    return agg_summary(con, "filter_current", verbose=verbose)


def create_filter_2019_summary(con, verbose=False):
    """make temp table filter_2019_day, group by station, aggregate by day"""
    return agg_summary(con, "filter_2019", verbose=verbose)


def create_filter_pandemic_summary(con, verbose=False):
    """make temp table filter_pandemic_day, group by station, aggregate by day"""
    return agg_summary(con, "filter_pandemic", verbose=verbose)


def query_value(con, query, verbose=False):
    """return a single query value"""
    return get_sql_from_template(con, query, None, verbose).iloc[0][0]


def entries_by_date(con, verbose=False):
    """return dataframe of all entries by date, subject to filters"""
    query = "select date, entries, exits from filter_current_summary order by date"
    return get_sql_from_template(con, query, None, verbose)


def entries_by_dow(con, verbose=False):
    """return dataframe of all entries by day of week, comps, subject to filters"""

    query = """
        (select
            'selection' as when,
            count(*) n,
            dow,
            sum(entries)/n as entries,
            sum(exits)/n as exits
        from filter_current_summary
        group by
            dow
        )
        union
        (select
            '2019' as when,
            count(*) n,
            dow,
            sum(entries)/n as entries,
            sum(exits)/n as exits
        from filter_2019_summary
        group by
            dow
        )
        union
        (select
            'pandemic' as when,
            count(*) n,
            dow,
            sum(entries)/n as entries,
            sum(exits)/n as exits
        from filter_pandemic_summary
        group by
            dow
        )
    """

    return get_sql_from_template(con, query, None, verbose=verbose)


def entries_by_tod(con, verbose=False):
    """return dataframe of all entries by time of day, subject to filters"""

    query = """
    (with cur as
        (select
            date,
            hour,
            sum(entries) as entries,
            sum(exits) as exits
        from filter_current
        group by
            date,
            hour)
    select 'selection' as when, hour, count(*) n, sum(entries)/n as entries, sum(exits)/n as exits from cur group by hour)

    union

    (with pand as
        (select
            date,
            hour,
            sum(entries) as entries,
            sum(exits) as exits
        from filter_pandemic
        group by
            date,
            hour)
    select 'pandemic' as when, hour, count(*) n, sum(entries)/n as entries, sum(exits)/n as exits from pand group by hour)

    union

    (with f19 as
        (select
            date,
            hour,
            sum(entries) as entries,
            sum(exits) as exits
        from filter_2019
        group by
            date,
            hour)
    select '2019' as when, hour, count(*) n, sum(entries)/n as entries, sum(exits)/n as exits from f19 group by hour)
    """

    return get_sql_from_template(con, query, None, verbose=verbose)


def entries_by_station(con, verbose=False):

    query = """
    with cur as
    (SELECT
        station,
        count(*) n,
        sum(entries)/n entries,
        sum(exits)/n exits
    from
        filter_current_daily
        group by station
    ),
    pand as
    (SELECT
        station,
        count(*) n,
        sum(entries)/n entries,
        sum(exits)/n exits
    from
        filter_pandemic_daily
        group by station
    ),
    f19 as
    (SELECT
        station,
        count(*) n,
        sum(entries)/n entries,
        sum(exits)/n exits
    from
        filter_2019_daily
        group by station
    )
    select
        station_list.pretty_name,
        latitude,
        longitude,
        cur.entries entries_selection,
        cur.exits exits_selection,
        pand.entries entries_pandemic,
        pand.exits exits_pandemic,
        f19.entries entries_2019,
        f19.exits exits_2019
    from
        station_list
        left outer join cur on station_list.pretty_name = cur.station
        left outer join f19 on station_list.pretty_name = f19.station
        left outer join pand on station_list.pretty_name = pand.station
    order by station_list.station;
    """

    return get_sql_from_template(con, query, None, verbose=verbose)

######################################################################
# output panels as elements
######################################################################


def text_panel_1(entries_daily, entries_pandemic, entries_2019):
    markdown1 = '''
| Avg Daily Entries: |  &nbsp; | {:,.0f} |
| -------- | - | ---: |
| Change vs. Pandemic: | &nbsp; &nbsp; | {:,.1f}% |
| Change vs. 2019: | &nbsp;| {:,.1f}%
'''

    return dcc.Markdown(markdown1.format(entries_daily,
                                         entries_daily/entries_pandemic*100-100,
                                         entries_daily/entries_2019*100-100))


def text_panel_2(entries_pandemic, entries_2019):
    markdown2 = '''
| Pandemic (4/20-3/21): |  &nbsp; | {:,.0f} |
| -------- | - | ---: |
| Change vs. 2019: |  &nbsp; &nbsp; | {:,.1f}% |'''

    return dcc.Markdown(markdown2.format(entries_pandemic,
                                         entries_pandemic/entries_2019*100-100))


def text_panel_3(entries_2019):
    markdown3 = '''
| 2019: | &nbsp; | {:,.0f} |
| -------- | - | ---: |
|      |         |'''
    return dcc.Markdown(markdown3.format(entries_2019))


def fig1(df_entries_by_date):
    fig = px.line(df_entries_by_date, x="date", y="entries", height=360)
    fig.update_traces(line=dict(color='#0033cc', width=2))
    fig.update_layout(
        margin={'l': 10, 'r': 15, 't': 10},
        paper_bgcolor="white",
        # plot_bgcolor="white",
        showlegend=False,
        xaxis_title="Date",
        yaxis_title="Entries",
        legend_title="Legend Title",
        xaxis={
            'ticks': 'inside',
            'showgrid': True,            # thin lines in the background
            'zeroline': False,           # thick line at x=0
            'visible': True,             # numbers below
            'showline': True,            # Show X-Axis
            'linecolor': 'black',        # Color of X-axis
            'tickfont_color': 'black',   # Color of ticks
            'showticklabels': True,      # Show X labels
            'mirror': True,              # draw right axis
        },
        yaxis={
            'ticks': 'inside',
            'showgrid': True,            # thin lines in the background
            'zeroline': False,           # thick line at x=0
            'visible': True,             # numbers below
            'showline': True,            # Show X-Axis
            'linecolor': 'black',        # Color of X-axis
            'tickfont_color': 'black',   # Color of ticks
            'showticklabels': True,      # Show X labels
            'side': 'left',
            'mirror': True,
        },
        #     font=dict(
        #         family="Courier New, monospace",
        #         size=18,
        #         color="RebeccaPurple"
        #     )
    )
    return dcc.Graph(id='entries-graph', figure=fig)


def fig2(df_entries_by_dow):
    # fix sort order
    df_entries_by_dow['Weekday'] = df_entries_by_dow['dow'].apply(lambda i: dowinvmap[i])

    fig = px.bar(df_entries_by_dow[['Weekday', 'when', 'entries']],
                 x="Weekday", y="entries", color='when', barmode="group", height=360,
                 color_discrete_sequence=plotly.colors.qualitative.Dark24)
    # fig.update_traces(marker_color='#003399')
    fig.update_layout(
        margin={'l': 10, 'r': 15, 't': 10},
        paper_bgcolor="white",
        # plot_bgcolor="white",
        showlegend=False,
        xaxis_title="Date",
        yaxis_title="Entries",
        legend_title="Legend Title",
        xaxis={
            'tickmode': 'linear',
            'tick0': 0,
            'dtick': 1,
            'title': 'Day of Week',
            'ticks': 'inside',
            'showgrid': True,            # thin lines in the background
            'zeroline': False,           # thick line at x=0
            'visible': True,             # numbers below
            'showline': True,            # Show X-Axis
            'linecolor': 'black',        # Color of X-axis
            'tickfont_color': 'black',   # Color of ticks
            'showticklabels': True,      # Show X labels
            'mirror': True,              # draw right axis
        },
        yaxis={
            'ticks': 'inside',
            'showgrid': True,            # thin lines in the background
            'zeroline': False,           # thick line at x=0
            'visible': True,             # numbers below
            'showline': True,            # Show X-Axis
            'linecolor': 'black',        # Color of X-axis
            'tickfont_color': 'black',   # Color of ticks
            'showticklabels': True,      # Show X labels
            'side': 'left',
            'mirror': True,
        },
    )
    return dcc.Graph(id='dow-graph', figure=fig)


def fig3(df_entries_by_tod):
    fig = px.bar(df_entries_by_tod,
                 x="hour", y="entries", color='when', barmode="group", height=360,
                 color_discrete_sequence=plotly.colors.qualitative.Dark24)
    fig.update_layout(
        margin={'l': 10, 'r': 15, 't': 10},
        paper_bgcolor="white",
        # plot_bgcolor="white",
        showlegend=False,
        xaxis_title="Date",
        yaxis_title="Entries",
        legend_title="Legend Title",
        xaxis={
            'tickmode': 'linear',
            'tick0': 0,
            'dtick': 4,
            'title': 'Time of Day',
            'ticks': 'inside',
            'showgrid': True,            # thin lines in the background
            'zeroline': False,           # thick line at x=0
            'visible': True,             # numbers below
            'showline': True,            # Show X-Axis
            'linecolor': 'black',        # Color of X-axis
            'tickfont_color': 'black',   # Color of ticks
            'showticklabels': True,      # Show X labels
            'mirror': True,              # draw right axis
        },
        yaxis={
            'ticks': 'inside',
            'showgrid': True,            # thin lines in the background
            'zeroline': False,           # thick line at x=0
            'visible': True,             # numbers below
            'showline': True,            # Show X-Axis
            'linecolor': 'black',        # Color of X-axis
            'tickfont_color': 'black',   # Color of ticks
            'showticklabels': True,      # Show X labels
            'side': 'left',
            'mirror': True,
        },
    )
    return dcc.Graph(id='entries-tod', figure=fig)


def fig_table(df):
    temp_df = df[['pretty_name', 'entries_selection', 'entries_pandemic', 'entries_2019']].copy()
    temp_df['pct_v_2019'] = temp_df['entries_selection'] / temp_df['entries_2019'] - 1
    temp_df['pct_v_pandemic'] = temp_df['entries_selection'] / temp_df['entries_pandemic'] - 1
    temp_df.rename(columns={'pretty_name': 'station', 'entries_selection': 'entries'}, inplace=True)

    table = dash_table.DataTable(
        id='fig_table',
        columns=[
            {"name": 'Station', "id": 'station', "deletable": False, "selectable": False},
            {"name": 'Avg Daily Entries', "id": 'entries', "deletable": False, "selectable": False,
             "type": "numeric", "format": Format(precision=0, scheme=Scheme.fixed)},
            {"name": '%Ch vs. 2019', "id": 'pct_v_2019', "deletable": False, "selectable": False,
             "type": "numeric", "format": FormatTemplate.percentage(1)},
            {"name": '%Ch vs. Pandemic', "id": 'pct_v_pandemic', "deletable": False, "selectable": False,
             "type": "numeric", "format": FormatTemplate.percentage(1)},
        ],
        data=temp_df.to_dict('records'),
        editable=False,
        filter_action="native",
        sort_action="native",
        sort_mode="single",
        row_selectable=False,
        row_deletable=False,
        selected_columns=[],
        selected_rows=[],
        page_action="native",
        page_current=0,
        page_size=15,
        style_header={
            'font-family': "Open Sans, Verdana, Calibri, Arial, Helvetica, Sans-serif",
            'backgroundColor': 'white',
            'fontWeight': 'bold'
        },
        style_cell={
            'font-family': '"Lucida Console", "Lucida Sans Typewriter", "Lucidatypewriter", "Monaco", "Andale Mono", "Consolas", "Courier New", "Courier", "Monospace"',
            'font-size': '14px',
        },
        style_cell_conditional=[
            {
                'if': {
                    'column_id': 'station',
                },
                'font-family': "Verdana, Calibri, Arial, Helvetica, Sans-serif",
            },
            {
                'if': {
                    'column_type': 'text'  # 'text' | 'any' | 'datetime' | 'numeric'
                },
                'textAlign': 'left'
            },
        ],
        style_data_conditional=[
            {
                'if': {
                    'column_editable': False  # True | False
                },
                'backgroundColor': 'rgb(240, 240, 240)',
                'cursor': 'not-allowed'
            },
        ]
    )
    return table


def fig_map(df, mapbox_token):
    df = df[['pretty_name', 'Latitude', 'Longitude', 'entries_selection',
             'entries_pandemic', 'entries_2019',]].copy()
    df['pct_v_2019'] = df['entries_selection'] / df['entries_2019'] - 1
    df['pct_v_pandemic'] = df['entries_selection'] / df['entries_pandemic'] - 1
    df.rename(columns={'pretty_name': 'station', 'entries_selection': 'entries'}, inplace=True)
    fig = px.scatter_mapbox(
        df,
        lat="Latitude",
        lon="Longitude",
        hover_name="station",
        hover_data={"entries": True, "Latitude": False, "Longitude": False,
                    "pct_v_2019": True, "pct_v_pandemic": True,
                    "entries_2019": False, "entries_pandemic": False},
        size="entries", size_max=20,
        color_continuous_scale=px.colors.sequential.YlGnBu, color="pct_v_2019",
        zoom=10, height=480)
    fig.update_layout(mapbox_style="carto-darkmatter", mapbox_accesstoken=mapbox_token)
    fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0}, showlegend=False)

    return dcc.Graph(id='fig_map', figure=fig)


######################################################################
# generate content
######################################################################

def generate_content(filters=None):

    return [
        # title
        dbc.Row([
            dbc.Col(xl=1),  # gutter on xl and larger
            dbc.Col(html.Div(html.H1(className="app-header",
                children=['MTA Turnstile Data'])))
            ]),

        ######################################################################
        # filters
        ######################################################################

        dbc.Row([
            dbc.Col(xl=1),  # gutter on xl and larger
            dbc.Col(html.Div([
                'Start date (>=):',
                dcc.DatePickerSingle(
                        id='start-date-picker-single',
                        min_date_allowed=date(2019, 1, 1),
                        max_date_allowed=datetime.today(),
                        initial_visible_month=date(2022, 1, 1),
                        date=date(2022, 1, 1)
                        ),
                'End date (<):',
                dcc.DatePickerSingle(
                        id='end-date-picker-single',
                        min_date_allowed=date(2019, 1, 1),
                        max_date_allowed=datetime.today(),
                        initial_visible_month=date(2023, 1, 1),
                        date=date(2023, 1, 1)
                        ),
                 ])),
        ]),
        dbc.Row([
            dbc.Col(xl=1),  # gutter on xl and larger
            dbc.Col([html.Div("Where:")], xs=2),
            dbc.Col(html.Div([
                dcc.Checklist(
                    ["Manhattan below 63 St", "Manhattan above 63 St", "Brooklyn", "Queens", "Bronx"],
                    ["Manhattan below 63 St", "Manhattan above 63 St", "Brooklyn", "Queens", "Bronx"],
                    id='checklist-borough',
                    className='mta-checklist',
                    inline=True,
                )
            ])),
        ]),
        dbc.Row([
            dbc.Col(xl=1),  # gutter on xl and larger
            dbc.Col([html.Div("Day of week:")], xs=2),
            dbc.Col(html.Div([
                dcc.Checklist(
                    ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday",],
                    ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday",],
                    id='checklist-dow',
                    className='mta-checklist',
                    inline=True,
                )
            ])),
        ]),
        dbc.Row([
            dbc.Col(xl=1),  # gutter on xl and larger
            dbc.Col([html.Div("Time of day:")], xs=2),
            dbc.Col(html.Div([
                dcc.Checklist(
                    ["4:00am", "8:00am", "12:00 noon", "4:00pm", "8:00pm", "12:00 midnight"],
                    ["4:00am", "8:00am", "12:00 noon", "4:00pm", "8:00pm", "12:00 midnight"],
                    id='checklist-tod',
                    className='mta-checklist',
                    inline=True,
                )
            ])),
        ]),
        dbc.Row([
            dbc.Col(xl=1),  # gutter on xl and larger
            dbc.Col([html.Div("Stations:")], xs=2),
            dbc.Col(html.Div([
                dcc.Dropdown(stations, None, id='dropdown-station', multi=True),
            ])),
            dbc.Col(xl=1),  # gutter on xl and larger
        ]),

        # dbc.Row([
        #     dbc.Col(xl=1),  # gutter on xl and larger
        #     dbc.Col([
        #         html.Button(id='submit-button-state', className='btn btn-primary', n_clicks=0, children='Submit')
        #         ])
        #     ]),
        # dbc.Row([
        #     dbc.Col(xl=1),  # gutter on xl and larger
        #     dbc.Col(html.Div(id='output-state'))
        #     ]),
        dbc.Row([
            dbc.Col(xl=1),  # gutter on xl and larger
            dbc.Col(html.Hr()),
            dbc.Col(xl=1),  # gutter on xl and larger
            ]),

        ######################################################################
        # output panels
        ######################################################################

        dbc.Row([
            dbc.Col(xl=1),  # gutter on xl and larger
            dbc.Col(html.Div(id="text_panel_1")),
            dbc.Col(html.Div(id="text_panel_2")),
            dbc.Col(html.Div(id="text_panel_3")),
            dbc.Col(xl=1),  # gutter on xl and larger
            ]),

        # spacer
        dbc.Row([
            dbc.Col(xl=1),  # gutter on xl and larger
            dbc.Col(html.Hr()),
            dbc.Col(xl=1),  # gutter on xl and larger
            ]),

        # headers
        dbc.Row([
            dbc.Col(xl=1),  # gutter on xl and larger
            dbc.Col(className="chart-header", children=['Entries by Date', ]),
            dbc.Col(className="chart-header", children=['Avg. Entries by Day of Week']),
            dbc.Col(className="chart-header", children=['Avg. Entries by 4-Hour Block']),
            dbc.Col(xl=1),  # gutter on xl and larger
            ]),
        dbc.Row([
            dbc.Col(xl=1),  # gutter on xl and larger
            dbc.Col(className="chart-header", id='fig1'),
            dbc.Col(className="chart-header", id='fig2'),
            dbc.Col(className="chart-header", id='fig3'),
            dbc.Col(xl=1),  # gutter on xl and larger
            ]),
        dbc.Row([
                dbc.Col(xl=1),
                dbc.Col(id='fig_table_parent'),
                dbc.Col(id='fig_map_parent'),
                dbc.Col(xl=1),
                ]),
    ]


######################################################################
# run the app
######################################################################

# global variable, only query on startup
stations = stations_fn(con, verbosity)

boromap = {
    'Manhattan below 63 St': 1,
    'Manhattan above 63 St': 2,
    'Brooklyn': 3,
    'Queens': 4,
    'Bronx': 5,
}

dowmap = {
    'Sunday': 0,
    'Monday': 1,
    'Tuesday': 2,
    'Wednesday': 3,
    'Thursday': 4,
    'Friday': 5,
    'Saturday': 6,
}
dowinvmap = {v: k for k, v in dowmap.items()}

todmap = {
    '4:00am': 4,
    '8:00am': 8,
    '12:00 noon': 12,
    '4:00pm': 16,
    '8:00pm': 20,
    '12:00 midnight': 24
}

app = Dash(__name__, external_stylesheets=[dbc.themes.SANDSTONE])
app.title = "Druce's MTA Dashboard"

app.layout = html.Div(generate_content(), id='div_toplevel')


@app.callback(Output('text_panel_1', 'children'),
              Output('text_panel_2', 'children'),
              Output('text_panel_3', 'children'),
              Output('fig1', 'children'),
              Output('fig2', 'children'),
              Output('fig3', 'children'),
              Output('fig_table_parent', 'children'),
              Output('fig_map_parent', 'children'),
              # Input('submit-button-state', 'n_clicks'),
              Input('start-date-picker-single', 'date'),
              Input('end-date-picker-single', 'date'),
              Input('checklist-borough', 'value'),
              Input('checklist-dow', 'value'),
              Input('checklist-tod', 'value'),
              Input('dropdown-station', 'value'),
              )
def update_output(startdate, enddate, boro, dow, tod, sta):

    filters = defaultdict(str)
    filters['startdate'] = startdate
    filters['enddate'] = enddate

    # print(boro)
    if boro and len(boro) < 5:  # if all are set, don't set a filter
        filters['boro'] = list(map(lambda s: boromap[s], boro))

    # print(dow)
    if dow and len(dow) < 7:  # if all are set, don't set a filter
        filters['dow'] = list(map(lambda s: dowmap[s], dow))

    # print(tod)
    if tod and len(tod) < 6:  # if all are set, don't set a filter
        filters['tod'] = list(map(lambda s: todmap[s], tod))

    # print(sta)
    if sta:
        filters['sta'] = sta

    # print(filters)

    create_filter_current(con, filters, verbose=verbosity)
    create_filter_pandemic(con, filters, verbose=verbosity)
    create_filter_2019(con, filters, verbose=verbosity)

    create_filter_current_daily(con, verbose=verbosity)
    create_filter_pandemic_daily(con, verbose=verbosity)
    create_filter_2019_daily(con, verbose=verbosity)

    create_filter_current_summary(con, verbose=verbosity)
    create_filter_pandemic_summary(con, verbose=verbosity)
    create_filter_2019_summary(con, verbose=verbosity)

    avg_entries_daily = query_value(con, "select avg(entries) from filter_current_summary", verbose=verbosity)
    avg_entries_pandemic = query_value(con, "select avg(entries) from filter_pandemic_summary", verbose=verbosity)
    avg_entries_2019 = query_value(con, "select avg(entries) from filter_2019_summary", verbose=verbosity)

    df_entries_by_date = entries_by_date(con, verbose=verbosity)
    df_entries_by_tod = entries_by_tod(con, verbose=verbosity)
    df_entries_by_dow = entries_by_dow(con, verbose=verbosity)
    df_entries_by_station = entries_by_station(con, verbose=verbosity)

    # output_state = u'''
    #     You have selected "{}" to "{}", borough "{}", DOW "{}", TOD"{}",
    # '''.format(startdate, enddate, borough, dow, tod)
    return [
        text_panel_1(avg_entries_daily, avg_entries_pandemic, avg_entries_2019),
        text_panel_2(avg_entries_pandemic, avg_entries_2019),
        text_panel_3(avg_entries_2019),
        fig1(df_entries_by_date),
        fig2(df_entries_by_dow),
        fig3(df_entries_by_tod),
        [fig_table(df_entries_by_station), html.Div(id='datatable-interactivity-container')],
        ["Station map, size=entries, color=%ch from 2019", fig_map(df_entries_by_station, mapbox_token),],
    ]

# check e.g. q line this year
# fix spacing of e.g. checkboxes
# check update on Saturdays


if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0')
