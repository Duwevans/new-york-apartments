# new-york-apartments

## Searching for an apartment share in NYC?
Well then I have an app for you!

new-york-apartments scrapes craigslist posts for apartment shared in 
NYC every 6 hours, returning the most recent posts found and
visualizations of the price points over time. The actual search on
craigslist can be pretty unpleasant - emailing random posts after hoping
something good pops up - and this app should be at the least informative
to anyone apartment hunting to get a sense of what's out there and
what's realistic to expect in the city. 

Data collection started in early April 2020.

Check out my post on [developing this dashboard.](https://medium.com/@duncanevans_72887/web-scraping-nyc-apartment-data-with-python-beautiful-soup-dash-and-heroku-4e0a5af40817)

This web scraping process is built with [Beautiful Soup](https://www.crummy.com/software/BeautifulSoup/bs4/doc/). 

The user interface is built in [Dash](https://dash.plotly.com/), which is an extension of 
[Plot.ly](https://plotly.com/). 

#### Possible future features:
* Data on full apartments per neighborhood (currently only rooms in apartment shares)
* Indication of whether or not a post is a good deal - compared to typical for the neighborhood
