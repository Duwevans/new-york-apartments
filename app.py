import dash
import dash_core_components as dcc
import dash_html_components as html
import pandas as pd
import numpy as np
import plotly.graph_objs as go
from dash.dependencies import Input, Output
import dash_table
import datetime as dt
import plotly.graph_objs as go
from datetime import datetime
import psycopg2
import os

pd.options.mode.chained_assignment = None  # default='warn'

external_stylesheets = ["https://stackpath.bootstrapcdn.com/bootstrap/4.1.3/css/bootstrap-grid.min.css"]

# amazon rds database connection
connection = psycopg2.connect(
host = os.environ['HOST'],
port = '5432',
user = 'duncan',
password = os.environ['PASSWORD'],
database = 'postgres'
)


def get_dataset(connection):
    """"""
    #  apartment_data = pd.read_csv('https://raw.githubusercontent.com/Duwevans/'
    #                             'new-york-apartments/master/apartment_data.csv')
    #  apartment_data['post_date'] = pd.to_datetime(apartment_data['post_datetime']).dt.date

    sql = """
    SELECT * FROM rooms;
    """
    apartment_data = pd.read_sql(sql, con=connection)

    apartment_data['post_date'] = pd.to_datetime(apartment_data['post_datetime']).dt.date

    return apartment_data


def apply_price_range_apartment_data(apartment_data, low_, high_):
    """returns apartment data between two price ranges"""
    apartment_data_filtered = apartment_data.loc[
        (apartment_data['post_price'] >= low_) & (apartment_data['post_price'] <= high_)
    ]

    return apartment_data_filtered


def get_posts_per_date(apartment_data):
    """find the counts of posts per date per neighborhood"""
    all_dates = pd.DataFrame()

    # loop through by date
    for d in apartment_data['post_date'].unique():
        df = apartment_data.loc[apartment_data['post_date'] == d]

        # counts by neighborhood
        dfx = pd.DataFrame(df['neighborhood'].value_counts()).rename(
            columns={'neighborhood': 'posts'}
        )
        dfx['neighborhood'] = dfx.index
        dfx = dfx.reset_index(drop=True)
        dfx['post_date'] = d
        all_dates = all_dates.append(dfx, sort=False)

    return all_dates


def get_median_price_per_date(apartment_data):
    """finds the median price of a posting per date per apartment"""
    all_prices = pd.DataFrame()
    # loop through by date
    for d in apartment_data['post_date'].unique():
        df = apartment_data.loc[apartment_data['post_date'] == d]

        # counts by neighborhood
        dfx = pd.DataFrame(pd.pivot_table(
            df,
            values='post_price',
            index='neighborhood',
            aggfunc=np.median
        )
        ).rename(columns={'post_price': 'median_price'})

        dfx['neighborhood'] = dfx.index
        dfx = dfx.reset_index(drop=True)
        dfx['post_date'] = d

        all_prices = all_prices.append(dfx, sort=False)

    return all_prices


def get_all_time_prices(apartment_data):
    """finds the all-time median and average price of each of the neighborhoods"""

    # median df
    dfx = pd.pivot_table(
        apartment_data,
        index='neighborhood',
        values='post_price',
        aggfunc=np.median
    )
    dfx['neighborhood'] = dfx.index
    dfx['post_price'] = round(dfx['post_price'], 0)
    df_median = dfx.reset_index(drop=True)

    # avg df
    dfx = pd.pivot_table(
        apartment_data,
        index='neighborhood',
        values='post_price',
        aggfunc=np.mean
    )
    dfx['neighborhood'] = dfx.index
    dfx['post_price'] = round(dfx['post_price'], 0)
    df_mean = dfx.reset_index(drop=True)

    return df_median, df_mean


def get_starting_data(connection):

    apartment_data = get_dataset(connection)

    all_dates = get_posts_per_date(apartment_data)

    all_prices = get_median_price_per_date(apartment_data)

    return apartment_data, all_dates, all_prices


# estimate apartment size/bedrooms
def determine_apt_size(post_title):
    """"""
    studio = ['studio']
    one_bed = ['1br', 'one bedroom', '1 bedroom', '1 br', '1 bdr', '1bdr']
    two_bed = ['2br', 'two bedroom', '2 bedroom', '2 br', '2 bdr', '2bdr']
    three_bed = ['3br', 'three bedroom', '3 bedroom', '3 br', '3 bdr', '3bdr']
    four_bed = ['4br', 'four bedroom', '4 bedroom', '4 br', '4 bdr', '4bdr']
    five_bed = ['5br', 'five bedroom', '5 bedroom', '5 br', '5 bdr', '5bdr']

    post_title = post_title.lower()

    if any(word in post_title for word in studio):
        apt_size = 'studio'
    elif any(word in post_title for word in one_bed):
        apt_size = 'one bedroom'
    elif any(word in post_title for word in two_bed):
        apt_size = 'two bedroom'
    elif any(word in post_title for word in three_bed):
        apt_size = 'three bedroom'
    elif any(word in post_title for word in four_bed):
        apt_size = 'four bedroom'
    elif any(word in post_title for word in five_bed):
        apt_size = 'five bedroom'
    else:
        apt_size = 'other'

    return apt_size


# find the most common neighborhoods
def get_most_common_neighborhoods(apartment_data):
    """"""

    most_common = pd.DataFrame(
        apartment_data['neighborhood'].value_counts()
    ).rename(
        columns={
            'neighborhood': 'count'
        }
    )
    most_common['neighborhood'] = most_common.index
    most_common = most_common.reset_index(drop=True)

    # get neighborhoods with at least 30 results
    most_common_neighborhoods = most_common.loc[most_common['count'] >= 30]

    return most_common_neighborhoods


# get major data sets
apartment_data, all_dates, all_prices = get_starting_data(connection)

median_prices, mean_prices = get_all_time_prices(apartment_data)

# determine size of the apartment
apartment_data['size'] = apartment_data.apply(
        lambda x: determine_apt_size(
            x['post_title_text']
            ),
        axis=1)

app = dash.Dash('apartments', external_stylesheets=external_stylesheets)
app.title = 'NYC Room $s'

server = app.server

most_common_apartments = get_most_common_neighborhoods(apartment_data)


# get count of all neighborhoods as a list
hoods = pd.DataFrame(apartment_data['neighborhood'].value_counts())
hoods['neighborhood'] = hoods.index
sorted_hoods = hoods['neighborhood'].tolist()

sizes = apartment_data['size'].unique().tolist()

# create the layout of the app
app.layout = html.Div([

    html.Div([html.H1("What Does a Room Cost in NYC?")], style={'textAlign': "center"}),
    html.Div([html.H5(
        "The data below details the monthly rent prices for single rooms in apartment shares across NYC neighborhoods. "
        "This data is scraped from advertisements posted on craigslist on a daily basis. "
        "Data collection started in April of 2020."
    )], style={'textAlign': "center"}),

    dcc.Markdown('''
    
        Looking for a room in which neighborhood(s):
        '''),

    dcc.Dropdown(
        id='hood_selection',
        options=[
            {'label': c, 'value': c}
            for c in sorted_hoods

        ],
        value=[
            'Upper East Side',
            'East Village',
            'Upper West Side',
        ],
        multi=True,
        clearable=False,
    ),

    dcc.Markdown('''
        Looking for a single room in which size apartment (two+ bedrooms are shared apartments):
        '''),
    # todo: room selector

    dcc.Dropdown(
        id='size_selection',
        options=[
            {'label': c, 'value': c}
            for c in sizes

        ],
        value=[
            'studio',
            'one bedroom',
            'two bedroom',
            'three bedroom',
            'four bedroom',
            'five bedroom',
            'other',
        ],
        multi=True,
        clearable=False,
    ),

    dcc.Markdown('''
        Looking with a price range of:
        '''),

    html.Div([
        dcc.RangeSlider(
            id='price_range_slider',
            min=1000,
            max=4000,
            step=50,
            marks={
                    1000: '$1000',
                    1500: '$1500',
                    2000: '$2000',
                    2500: '$2500',
                    3000: '$3000',
                    3500: '$3500',
                },
            value=[1000, 2500],
            allowCross=False

        ),
    ]),
    dcc.Markdown('''
        
        Showing apartments from: 
        '''),
    dcc.Markdown('''

        '''),

    html.Div(id='output-container-range-slider'),

    html.Div([
            dcc.Graph(id='post_by_date_series'),
        ]),
    html.Div([
            dcc.Graph(id='price_by_date_series'),
        ]),
    html.Div([
            dcc.Graph(id='all_prices_histogram'),
        ]),

    dcc.Markdown('''

    ##### I found the following posts for you:
    '''),

    # data table
    html.Div([
        dash_table.DataTable(
            id='recent_posts_table',
            columns=[
                {'name': 'Neighborhood', 'id': 'neighborhood'},
                {'name': 'Price', 'id': 'post_price'},
                {'name': 'Title', 'id': 'post_title_text'},
                {'name': 'Date', 'id': 'post_date'},
                {'name': 'Size', 'id': 'size'},
                {'name': 'Link', 'id': 'post_link'},
            ],
            style_table={
                    'maxHeight': '500px',
                    'overflowY': 'scroll',
    },
        ),
    ]),

    dcc.Markdown('''
    ##### These are the all-time prices for the neighborhoods you're looking in:
    '''),
    html.Div([
        html.Div([
            dcc.Graph(id='all_time_median_chart'),
        ],
            style={'width': '48%', 'display': 'inline-block', 'align': 'left'}),

        html.Div([
            dcc.Graph(id='all_time_average_chart'),
        ],
            style={'width': '48%', 'display': 'inline-block', 'align': 'right'})
    ],
        ),

    dcc.Markdown('''
    ##### These are the all-time prices for all neighborhoods in dataset:
    '''),
    html.Div([
        html.Div([
            dcc.Graph(id='all_time_median_chart_all_neighborhoods'),
        ],
            style={'width': '48%', 'display': 'inline-block', 'align': 'left'}),

        html.Div([
            dcc.Graph(id='all_time_mean_chart_all_neighborhoods'),
        ],
            style={'width': '48%', 'display': 'inline-block', 'align': 'right'})
    ],
        ),

])


@app.callback(
    dash.dependencies.Output('output-container-range-slider', 'children'),
    [dash.dependencies.Input('price_range_slider', 'value')])
def update_range_output(value):
    low_ = value[0]
    high_ = value[1]

    return "\n\n$" + str(low_) + " to $" + str(high_) + " monthly"


@app.callback(
    Output('post_by_date_series', 'figure'),
    [Input('hood_selection', 'value'),
     Input('price_range_slider', 'value'),
     Input('size_selection', 'value')]
)
def update_posts_by_date_series(neighborhoods, price_range, sizes):
    """"""

    # get apartment data within price range
    apartment_data_filtered = apply_price_range_apartment_data(
        apartment_data, price_range[0], price_range[1]
    )

    # filter to room size selections
    apartment_data_filtered = apartment_data_filtered.loc[
        apartment_data_filtered['size'].isin(sizes)
    ]

    all_dates = get_posts_per_date(apartment_data_filtered)

    all_traces = []
    for neighborhood in neighborhoods:
        neighborhood_df = all_dates.loc[all_dates['neighborhood'] == neighborhood]

        neighborhood_df['post_date'] = pd.to_datetime(neighborhood_df['post_date'])
        neighborhood_df = neighborhood_df.sort_values(by='post_date')
        neighborhood_df['post_date_delta'] = (neighborhood_df['post_date'] - pd.to_datetime('04/08/2020')).dt.days
        neighborhood_df['format_date'] = neighborhood_df['post_date'].dt.strftime("%Y-%m-%d")

        # scatter trace per neighborhood
        trace = go.Scatter(
            x=neighborhood_df['post_date'],
            y=neighborhood_df['posts'],
            name=neighborhood,
            opacity = 0.8
        )

        all_traces.append(trace)

    layout = go.Layout(
        title = "Count of Posts per Date",
        xaxis = {"title": "Date",
                 "type": "date",
                 #  "range": ['2020-04-01', '2020-04-30'],
                 },
        yaxis = {"title": "Count of Posts",
                 "range": [0, 35]},

    )
    #  print(all_traces)

    figure = {'data': all_traces, 'layout': layout}

    return figure


@app.callback(
    Output('price_by_date_series', 'figure'),
    [Input('hood_selection', 'value',),
     Input('price_range_slider', 'value'),
     Input('size_selection', 'value')]
)
def update_price_by_date_series(neighborhoods, price_range, sizes):
    """"""

    # get apartment data within price range
    apartment_data_filtered = apply_price_range_apartment_data(
        apartment_data, price_range[0], price_range[1]
    )

    # filter to room size selections
    apartment_data_filtered = apartment_data_filtered.loc[
        apartment_data_filtered['size'].isin(sizes)
    ]

    all_prices = get_median_price_per_date(apartment_data_filtered)

    all_traces = []
    for neighborhood in neighborhoods:
        neighborhood_df = all_prices.loc[all_prices['neighborhood'] == neighborhood]

        neighborhood_df['post_date'] = pd.to_datetime(neighborhood_df['post_date'])
        neighborhood_df = neighborhood_df.sort_values(by='post_date')
        neighborhood_df['post_date_delta'] = (neighborhood_df['post_date'] - pd.to_datetime('04/08/2020')).dt.days
        neighborhood_df['format_date'] = neighborhood_df['post_date'].dt.strftime("%Y-%m-%d")

        # scatter trace per neighborhood
        trace = go.Scatter(
            x=neighborhood_df['post_date'],
            y=neighborhood_df['median_price'],
            name=neighborhood,
            opacity = 0.8,
        )

        all_traces.append(trace)

    layout = go.Layout(
        title = "Median Monthly Rent per Date",
        xaxis = {"title": "Date",
                 "type": "date",
                 #  "range": ['2020-04-01', '2020-04-30'],
                 },
        yaxis = {
            "title": "Median Rent",
            "range": [0, 3000]
        },

    )

    figure = {'data': all_traces, 'layout': layout}

    return figure


# all time median price
@app.callback(
    Output('all_time_median_chart', 'figure'),
    [Input('hood_selection', 'value')]
)
def update_price_by_date_series(neighborhoods):
    """"""

    neighborhood_df = median_prices.loc[median_prices['neighborhood'].isin(neighborhoods)].sort_values(
        by='post_price', ascending=True
    )

    # scatter trace per neighborhood
    trace = go.Bar(
        x=neighborhood_df['post_price'],
        y=neighborhood_df['neighborhood'],
        orientation='h',
        opacity = 0.8,
        textposition='auto',
        text=neighborhood_df['post_price']
    )

    layout = go.Layout(
        title = "Median Monthly Rent by Neighborhood",
        xaxis = {"title": "Median Rent",

                 },
        yaxis = {"title": "neighborhood",
                 'automargin': True,
                 },

    )

    figure = {'data': [trace], 'layout': layout}

    return figure


# all time median price for all neighborhoods
@app.callback(
    Output('all_time_median_chart_all_neighborhoods', 'figure'),
    [Input('size_selection', 'value')]
)
def update_median_all_neighborhoods(sizes):
    """"""

    df = apartment_data.loc[apartment_data['size'].isin(sizes)]
    df = df.loc[df['neighborhood'].isin(most_common_apartments['neighborhood'])]

    df_median, df_mean = get_all_time_prices(df)

    neighborhood_df = df_median.sort_values(
        by='post_price', ascending=True
    )

    # scatter trace per neighborhood
    trace = go.Bar(
        x=neighborhood_df['post_price'],
        y=neighborhood_df['neighborhood'],
        orientation='h',
        opacity = 0.8,
        textposition='auto',
        text=neighborhood_df['post_price']
    )

    layout = go.Layout(
        title = "Median Monthly Rent by Neighborhood",
        xaxis = {"title": "Median Rent",

                 },
        yaxis = {"title": "neighborhood",
                 'automargin': True,
                 },

    )

    figure = {'data': [trace], 'layout': layout}

    return figure


# all time mean price for all neighborhoods
@app.callback(
    Output('all_time_mean_chart_all_neighborhoods', 'figure'),
    [Input('size_selection', 'value')]
)
def update_mean_all_neighborhoods(sizes):
    """"""

    df = apartment_data.loc[apartment_data['size'].isin(sizes)]
    df = df.loc[df['neighborhood'].isin(most_common_apartments['neighborhood'])]

    df_median, df_mean = get_all_time_prices(df)

    neighborhood_df = df_mean.sort_values(
        by='post_price', ascending=True
    )

    # scatter trace per neighborhood
    trace = go.Bar(
        x=neighborhood_df['post_price'],
        y=neighborhood_df['neighborhood'],
        orientation='h',
        opacity = 0.8,
        textposition='auto',
        text=neighborhood_df['post_price']
    )

    layout = go.Layout(
        title = "Average Monthly Rent by Neighborhood",
        xaxis = {"title": "Average Rent",

                 },
        yaxis = {"title": "neighborhood",
                 'automargin': True,
                 },

    )

    figure = {'data': [trace], 'layout': layout}

    return figure


@app.callback(
    Output('all_time_average_chart', 'figure'),
    [Input('hood_selection', 'value')]
)
def update_price_by_date_series(neighborhoods):
    """"""

    neighborhood_df = mean_prices.loc[mean_prices['neighborhood'].isin(neighborhoods)].sort_values(
        by='post_price', ascending=True
    )

    # scatter trace per neighborhood
    trace = go.Bar(
        x=neighborhood_df['post_price'],
        y=neighborhood_df['neighborhood'],
        orientation='h',
        opacity = 0.8,
        textposition='auto',
        text=neighborhood_df['post_price']
    )

    layout = go.Layout(
        title = "Average Monthly Rent by Neighborhood",
        xaxis = {"title": "Average Rent",

                 },
        yaxis = {"title": "neighborhood",
                 'automargin': True,

                 },

    )

    figure = {'data': [trace], 'layout': layout}

    return figure


# histogram of all prices
@app.callback(
    Output('all_prices_histogram', 'figure'),
    [Input('hood_selection', 'value'),
     Input('price_range_slider', 'value'),
     Input('size_selection', 'value')]
)
def update_all_prices_histogram(neighborhoods, price_range, sizes):
    """"""
    # get apartment data within price range
    apartment_data_filtered = apply_price_range_apartment_data(
        apartment_data, price_range[0], price_range[1]
    )

    # filter to room size selections
    apartment_data_filtered = apartment_data_filtered.loc[
        apartment_data_filtered['size'].isin(sizes)
    ]

    all_traces = []
    for neighborhood in neighborhoods:
        neighborhood_df = apartment_data_filtered.loc[
            apartment_data_filtered['neighborhood'] == neighborhood]

        trace = go.Histogram(
            x=neighborhood_df['post_price'],
            name=neighborhood,
        )
        all_traces.append(trace)

    layout = go.Layout(
        title="Distribution of Monthly Rent by Neighborhood",
        xaxis={'title': 'Monthly Rent'},
        yaxis={'title': 'count', },
        bargap=0.1,
    )

    figure = {'data': all_traces, 'layout': layout}

    return figure


@app.callback(
    Output('recent_posts_table', 'data'),
    [Input('hood_selection', 'value'),
     Input('price_range_slider', 'value'),
     Input('size_selection', 'value')]
)
def update_recent_posts_table(neighborhoods, price_range, sizes):
    """returns a table of the most recent apartment posts"""
    # get apartment data within price range
    apartment_data_filtered = apply_price_range_apartment_data(
        apartment_data, price_range[0], price_range[1]
    )

    apartment_data_filtered = apartment_data_filtered.loc[
        apartment_data_filtered['neighborhood'].isin(neighborhoods)
    ]

    # filter to room size selections
    apartment_data_filtered = apartment_data_filtered.loc[
        apartment_data_filtered['size'].isin(sizes)
    ]

    # sort by most recent posts
    apartment_data_filtered = apartment_data_filtered.sort_values(by=['post_datetime'], ascending=False)

    data = apartment_data_filtered.to_dict(orient='records')

    return data


# todo: all neighborhood price chart


if __name__ == '__main__':
    app.run_server(debug=True)
