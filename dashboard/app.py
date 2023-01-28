import os
from time import strftime
from datetime import date

from collections import defaultdict
from six import string_types
from copy import deepcopy

import pandas as pd

# import plotly
import plotly.express as px
from dash import Dash, html, dcc, dash_table
from dash.dash_table import DataTable, FormatTemplate
from dash.dash_table.Format import Format, Scheme

import sqlalchemy
from jinjasql import JinjaSql
import dash_bootstrap_components as dbc

# import duckdb

verbosity = 1

DATADIR = os.getenv('DATADIR')
if not DATADIR:
    print("%s - DATADIR environment variable not defined, exiting" % strftime("%H:%M:%S"))
    exit(1)
DATAFILE = os.getenv('DATAFILE')
DATAPATH = "%s/%s" % (DATADIR, DATAFILE)

STARTDATE = os.getenv('STARTDATE')
if not STARTDATE:
    START_DATE = date(2022, 1, 1)
    END_DATE = date.today()

mapbox_token = os.getenv('MAPBOX_TOKEN')

filters = defaultdict(str)

filters['dow'] = [
    'Monday',
    'Tuesday',
    'Wednesday',
    'Thursday',
    'Friday',
    # 'Saturday',
    # 'Sunday', 
    ]
filters['tod'] = [4, 8, 12, 16, 20, 24]
filters['cbd'] = ['Y', 'N']
filters['startdate'] = '2022-01-01'
filters['enddate'] = '2023-01-01'

filters['pandemic_start'] = '2020-03-01'
filters['pandemic_end'] = '2021-03-01'

connection_string = 'duckdb:////%s' % DATAPATH
con = sqlalchemy.create_engine(connection_string, connect_args={'read_only': True})

############################################################
# sql functions and queries - move to module
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
            return pd.read_sql(query, con, params={'read_only': True})

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


############################################################
# queries to return dataframes for dashboard
############################################################


def day_count(con, filters, verbose=False):
    """return number of days in the filter"""

    query = """

    select count(*) as days from
    (select
        date, count(*) as n
    from
        station_hourly
    where TRUE
        {% if startdate %} and date >= {{startdate}} {% endif %}
        {% if enddate %} and date < {{enddate}} {% endif %}
        {% if dow %} and dow in {{ dow | inclause }}  {% endif %}
        {% if tod %} and hour in {{ tod | inclause }} {% endif %}
        {% if cbd %} and cbd in {{ cbd | inclause }} {% endif %}
    group by
        "date"
    )
    """

    return get_sql_from_template(con, query, filters, verbose)


def day_count_pandemic(con, filters, verbose=False):
    """return number of days in the filter"""

    query = """

    select count(*) as days from
    (select
        date, count(*) as n
    from
        station_hourly
    where
        date >= {{pandemic_start}} and date < {{pandemic_end}}
        {% if dow %} and dow in {{ dow | inclause }}  {% endif %}
        {% if tod %} and hour in {{ tod | inclause }} {% endif %}
        {% if cbd %} and cbd in {{ cbd | inclause }} {% endif %}
    group by
        "date"
    )
    """

    return get_sql_from_template(con, query, filters, verbose)


def day_count_2019(con, filters, verbose=False):
    """return number of days in the filter"""

    query = """

    select count(*) as days from
    (select
        date, count(*) as n
    from
        station_hourly
    where
        date_part('year', DATE)=2019
        {% if dow %} and dow in {{ dow | inclause }}  {% endif %}
        {% if tod %} and hour in {{ tod | inclause }} {% endif %}
        {% if cbd %} and cbd in {{ cbd | inclause }} {% endif %}
    group by
        "date"
    )
    """

    return get_sql_from_template(con, query, filters, verbose)


def entries_by_date(con, filters, verbose=False):
    """return dataframe of all entries by date, subject to filters"""

    query = """
    select date, sum(entries) entries
    from station_hourly
    where TRUE
    {% if startdate %} and date >= {{startdate}} {% endif %}
    {% if enddate %} and date < {{enddate}} {% endif %}
    {% if dow %} and dow in {{ dow | inclause }}  {% endif %}
    {% if tod %} and hour in {{ tod | inclause }} {% endif %}
    {% if cbd %} and cbd in {{ cbd | inclause }} {% endif %}
    group by date
    order by date
    """

    return get_sql_from_template(con, query, filters, verbose)


def entries_by_tod(con, filters, verbose=False):
    """return dataframe of all entries by time of day, subject to filters"""

    query = """
    select
        hour,
        sum(entries) as entries,
    from
        station_hourly
    where TRUE
    {% if startdate %} and date >= {{startdate}} {% endif %}
    {% if enddate %} and date < {{enddate}} {% endif %}
    {% if dow %} and dow in {{ dow | inclause }}  {% endif %}
    {% if tod %} and hour in {{ tod | inclause }} {% endif %}
    {% if cbd %} and cbd in {{ cbd | inclause }} {% endif %}

    group by
        hour
    """

    return get_sql_from_template(con, query, filters, verbose)


def entries_by_dow(con, filters, verbose=False):
    """return dataframe of all entries by day of week, subject to filters"""

    query = """
    select
        dow,
        sum(entries) as entries,
    from
        station_hourly
    where TRUE
    {% if startdate %} and date >= {{startdate}} {% endif %}
    {% if enddate %} and date < {{enddate}} {% endif %}
    {% if dow %} and dow in {{ dow | inclause }}  {% endif %}
    {% if tod %} and hour in {{ tod | inclause }} {% endif %}
    {% if cbd %} and cbd in {{ cbd | inclause }} {% endif %}

    group by
        dow
    """

    return get_sql_from_template(con, query, filters, verbose)


def entries_by_station(con, filters, verbose=False):
    """
    query from hourly subject to filters, then sum by station
    include comparison to 2019 and pandemic (also subject to filters)
    """

    query = """
    with sd as
        (SELECT
        pretty_name,
        latitude,
        longitude,
        sum(entries) as entries
        FROM station_hourly
        where
            TRUE
            {% if startdate %} and date >= {{startdate}} {% endif %}
            {% if enddate %} and date < {{enddate}} {% endif %}
            {% if dow %} and dow in {{ dow | inclause }}  {% endif %}
            {% if tod %} and hour in {{ tod | inclause }} {% endif %}
            {% if cbd %} and cbd in {{ cbd | inclause }} {% endif %}
        GROUP BY
        pretty_name,
        latitude,
        longitude
        ORDER BY
        pretty_name
        )
    select
    sd.pretty_name,
    latitude,
    longitude,
    sd.entries,
    sd.entries::float/vs2019.entries_2019-1 as pct_v_2019,
    sd.entries::float/vspandemic.entries_pandemic-1 as pct_v_pandemic,
    vs2019.entries_2019,
    vspandemic.entries_pandemic
    FROM
    sd
    LEFT OUTER JOIN (
        SELECT pretty_name, sum(entries) entries_2019
            FROM station_hourly
            WHERE date_part('year', DATE)=2019
            {% if dow %} and dow in {{ dow | inclause }}  {% endif %}
            {% if tod %} and hour in {{ tod | inclause }} {% endif %}
            {% if cbd %} and cbd in {{ cbd | inclause }} {% endif %}
            GROUP BY pretty_name
            ORDER BY pretty_name
    ) vs2019 on vs2019.pretty_name=sd.pretty_name
    LEFT OUTER JOIN (
        SELECT pretty_name, sum(entries) entries_pandemic
            FROM station_hourly
            WHERE
            date >= {{pandemic_start}} and date < {{pandemic_end}}
            {% if dow %} and dow in {{ dow | inclause }}  {% endif %}
            {% if tod %} and hour in {{ tod | inclause }} {% endif %}
            {% if cbd %} and cbd in {{ cbd | inclause }} {% endif %}
            GROUP BY pretty_name
            ORDER BY pretty_name
    ) vspandemic on vspandemic.pretty_name=sd.pretty_name
    """

    return get_sql_from_template(con, query, filters, verbose)


# run the queries
df_day_count = day_count(con, filters)
day_count = df_day_count.iloc[0][0]
df_day_count_2019 = day_count_2019(con, filters)
day_count_2019 = df_day_count_2019.iloc[0][0]
df_day_count_pandemic = day_count_pandemic(con, filters)
day_count_pandemic = df_day_count_pandemic.iloc[0][0]

print("%d days, 2019 %d, pandemic %d" % (day_count, day_count_2019, day_count_pandemic))

df_entries_by_date = entries_by_date(con, filters, verbose=verbosity)
df_entries_by_tod = entries_by_tod(con, filters, verbose=verbosity)
df_entries_by_dow = entries_by_dow(con, filters, verbose=verbosity)
df_entries_by_station = entries_by_station(con, filters, verbose=verbosity)

entries_daily = df_entries_by_station['entries'].sum() / day_count
entries_2019 = df_entries_by_station['entries_2019'].sum() / day_count_2019
entries_pandemic = df_entries_by_station['entries_pandemic'].sum() / day_count_pandemic
df_entries_by_station['entries'] /= day_count
df_entries_by_dow['entries'] /= day_count
df_entries_by_tod['entries'] /= day_count

print("%f avg daily entries, 2019 %f, pandemic %f" % (entries_daily, entries_2019, entries_pandemic))

# output the dashboard
# show both ma and actual
fig1 = px.line(df_entries_by_date, x="DATE", y="entries", height=360)
fig1.update_traces(line=dict(width=2))
fig1.update_layout(
    paper_bgcolor="LightSteelBlue",
    showlegend=False,
    plot_bgcolor="white",
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

fig2 = px.bar(df_entries_by_dow, x="dow", y="entries", barmode="group", height=360)
fig2.update_layout(
    paper_bgcolor="LightSteelBlue",
    showlegend=False,
    plot_bgcolor="white",
    xaxis_title="Date",
    yaxis_title="Entries",
    legend_title="Legend Title",
    xaxis={
        'tickmode': 'linear',
        'tick0': 0,
        'dtick': 1,
        'title': None,
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

fig3 = px.bar(df_entries_by_tod, x="hour", y="entries", barmode="group", height=360)
fig3.update_layout(
    paper_bgcolor="LightSteelBlue",
    showlegend=False,
    plot_bgcolor="white",
    xaxis_title="Date",
    yaxis_title="Entries",
    legend_title="Legend Title",
    xaxis={
        'tickmode': 'linear',
        'tick0': 0,
        'dtick': 4,
        'title': 'Time of day',
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

df = df_entries_by_station
df['2022 Avg Daily Entries'] = df['entries'].apply(lambda f: "%.1fk" % (f/1000))
df['2022 vs. 2019'] = df['pct_v_2019'].apply(lambda f: "%.1f%%" % (f * 100))
df['2022 vs. Pandemic'] = df['pct_v_pandemic'].apply(lambda f: "%.1f%%" % (f * 100))

table = dash_table.DataTable(
    id='datatable-interactivity',
    columns=[{"name": 'Station', "id": 'pretty_name', "deletable": False, "selectable": False},
                {"name": 'Avg Daily Entries', "id": 'entries', "deletable": False, "selectable": False, "type": "numeric", "format": Format(precision=0, scheme=Scheme.fixed)},
                {"name": '%Ch From 2019', "id": 'pct_v_2019', "deletable": False, "selectable": False, "type": "numeric", "format": FormatTemplate.percentage(1)},
                {"name": '%Ch From Pandemic', "id": 'pct_v_pandemic', "deletable": False, "selectable": False, "type": "numeric", "format": FormatTemplate.percentage(1)},
                ],
    data=df[['pretty_name', 'entries', 'pct_v_2019', 'pct_v_pandemic']].to_dict('records'),
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
        'font-family': "Verdana, Calibri, Arial, Helvetica, Sans-serif",
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
                'column_id': 'pretty_name',
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

fig_map = px.scatter_mapbox(
    df,
    lat="Latitude",
    lon="Longitude",
    hover_name="pretty_name",
    hover_data={"2022 Avg Daily Entries": True,
                "2022 vs. Pandemic": True,
                "2022 vs. 2019": True,
                "entries": False,
                "Latitude": False,
                "Longitude": False,
                },
    size="entries", size_max=20,
    color_continuous_scale=px.colors.sequential.Jet, color="2022 vs. 2019",
    zoom=10, height=480)
fig_map.update_layout(mapbox_style="carto-darkmatter", mapbox_accesstoken=mapbox_token)
fig_map.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0}, showlegend=False)


app = Dash(external_stylesheets=[dbc.themes.SANDSTONE])

app.layout = html.Div(
    [
        dbc.Row([
            dbc.Col(xl=1),  # gutter on xl and larger
            dbc.Col(html.Div(html.H1(children=['MTA Turnstile Data', html.Hr()])))
            ]),

        dbc.Row([
            dbc.Col(xl=1),  # gutter on xl and larger
            dbc.Col(html.Div(html.H2(children='Average Daily Entries')))
            ]),

        dbc.Row([
            dbc.Col(xl=1),  # gutter on xl and larger
            dbc.Col(html.Div(dcc.Markdown('''
### Selected Period: {:,.0f} Entries
### Change from Pandemic: {:,.1f}%
### Change from 2019: {:,.1f}%'''.format(entries_daily, entries_daily/entries_pandemic*100-100, entries_daily/entries_2019*100-100)))),
            dbc.Col(html.Div(dcc.Markdown('''
### Pandemic: {:,.0f} Entries
### Change from 2019: {:,.1f}%'''.format(entries_pandemic, entries_pandemic/entries_2019*100-100)))),
            dbc.Col(html.Div(dcc.Markdown('''
### 2019: {:,.0f} Entries'''.format(entries_2019)))),
            dbc.Col(xl=1),  # gutter on xl and larger
            ]),

        dbc.Row([
            dbc.Col(xl=1),  # gutter on xl and larger
            dbc.Col(children=['Daily Entries', dcc.Graph(id='entries-graph', figure=fig1)]),
            dbc.Col(children=['Entries by Day of Week', dcc.Graph(id='entries-dow', figure=fig2)]),
            dbc.Col(children=['Entries by 4-Hour Block', dcc.Graph(id='entries-tod', figure=fig3)]),
            dbc.Col(xl=1),  # gutter on xl and larger
            ]),
        # spacer
        dbc.Row([
            dbc.Col(xl=1),  # gutter on xl and larger
            dbc.Col(html.Hr()),
            dbc.Col(xl=1),  # gutter on xl and larger
            ]),

        dbc.Row([
                dbc.Col(xl=1),
                dbc.Col(children=[
                    html.Div([table, html.Div(id='datatable-interactivity-container')])]),
                dbc.Col(children=['Map station entries and %ch', dcc.Graph(id='map-graph', figure=fig_map)]),
                dbc.Col(xl=1),
                ]),
    ]
)

app.run_server(debug=True)
