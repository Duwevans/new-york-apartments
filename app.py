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

pd.options.mode.chained_assignment = None  # default='warn'

external_stylesheets = ["https://stackpath.bootstrapcdn.com/bootstrap/4.1.3/css/bootstrap-grid.min.css"]


def get_dataset():
    """"""
    apartment_data = pd.read_csv('https://raw.githubusercontent.com/Duwevans/'
                                 'new-york-apartments/master/apartment_data.csv')
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


def get_starting_data():

    apartment_data = get_dataset()

    all_dates = get_posts_per_date(apartment_data)

    all_prices = get_median_price_per_date(apartment_data)

    return apartment_data, all_dates, all_prices


# get major data sets
apartment_data, all_dates, all_prices = get_starting_data()

median_prices, mean_prices = get_all_time_prices(apartment_data)


app = dash.Dash('apartments', external_stylesheets=external_stylesheets)


# get count of all neighborhoods as a list
hoods = pd.DataFrame(apartment_data['neighborhood'].value_counts())
hoods['neighborhood'] = hoods.index
sorted_hoods = hoods['neighborhood'].tolist()

# create the layout of the app
app.layout = html.Div([


    dcc.Markdown('''
    
        Select neighborhood:
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
            'Williamsburg',
            'Upper West Side',
        ],
        multi=True,
        clearable=False,
    ),

    dcc.Markdown('''

        Select price range:
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

    Posts found:
    '''),

    # todo: data table
    html.Div([
        dash_table.DataTable(
            id='recent_posts_table',
            columns=[
                {'name': 'Neighborhood', 'id': 'neighborhood'},
                {'name': 'Price', 'id': 'post_price'},
                {'name': 'Title', 'id': 'post_title_text'},
                {'name': 'Date', 'id': 'post_date'},
                {'name': 'Link', 'id': 'post_link'},
            ],
            style_table={
                    'maxHeight': '500px',
                    'overflowY': 'scroll',
    },
        ),
    ])
])


@app.callback(
    dash.dependencies.Output('output-container-range-slider', 'children'),
    [dash.dependencies.Input('price_range_slider', 'value')])
def update_range_output(value):
    low_ = value[0]
    high_ = value[1]

    return "Showing apartments from $" + str(low_) + " to $" + str(high_)


@app.callback(
    Output('post_by_date_series', 'figure'),
    [Input('hood_selection', 'value'),
     Input('price_range_slider', 'value')]
)
def update_posts_by_date_series(neighborhoods, price_range):
    """"""

    # get apartment data within price range
    apartment_data_filtered = apply_price_range_apartment_data(
        apartment_data, price_range[0], price_range[1]
    )

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
                 "range": ['2020-04-01', '2020-04-30'],
                 },
        yaxis = {"title": "Count of Posts",
                 "range": [0, 25]},

    )
    #  print(all_traces)

    figure = {'data': all_traces, 'layout': layout}

    return figure


@app.callback(
    Output('price_by_date_series', 'figure'),
    [Input('hood_selection', 'value',),
     Input('price_range_slider', 'value')]
)
def update_price_by_date_series(neighborhoods, price_range):
    """"""

    # get apartment data within price range
    apartment_data_filtered = apply_price_range_apartment_data(
        apartment_data, price_range[0], price_range[1]
    )

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
                 "range": ['2020-04-01', '2020-04-30'],
                 },
        yaxis = {"title": "Median Rent",
                 "range": [0, 3000]},

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
     Input('price_range_slider', 'value')]
)
def update_all_prices_histogram(neighborhoods, price_range):
    """"""
    # get apartment data within price range
    apartment_data_filtered = apply_price_range_apartment_data(
        apartment_data, price_range[0], price_range[1]
    )

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


# todo: table of most recent posts
@app.callback(
    Output('recent_posts_table', 'data'),
    [Input('hood_selection', 'value'),
     Input('price_range_slider', 'value')]
)
def update_recent_posts_table(neighborhoods, price_range):
    """"""
    # get apartment data within price range
    apartment_data_filtered = apply_price_range_apartment_data(
        apartment_data, price_range[0], price_range[1]
    )

    apartment_data_filtered = apartment_data_filtered.loc[
        apartment_data_filtered['neighborhood'].isin(neighborhoods)
    ]

    data = apartment_data_filtered.to_dict(orient='records')

    return data


if __name__ == '__main__':
    app.run_server(debug=True)
