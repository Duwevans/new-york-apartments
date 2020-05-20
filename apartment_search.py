from requests import get
from bs4 import BeautifulSoup
import pandas as pd
from time import sleep
from random import randint
import os
import sqlalchemy
from sqlalchemy import create_engine
import psycopg2
from psycopg2 import IntegrityError, errors
from datetime import datetime
import datetime as dt


pd.options.mode.chained_assignment = None  # default='warn'


def get_apartment_data(searches):
    """main function for searching apartment postings"""

    all_apartments = pd.DataFrame()

    # loop through each of the locations
    for location, link in searches.items():

        # momentary sleep
        sleep(randint(1, 5))

        response = get(link)

        html_soup = BeautifulSoup(response.text, 'html.parser')

        posts = html_soup.find_all('li', class_= 'result-row')
        print('location: ' + location + "\nposts found: " + str(len(posts)) + "\n")

        # loop through each of the posts
        for i in range(0, (len(posts) - 1)):
            post = posts[i]

            # skip if the neighborhood is not available
            if post.find('span', class_ = 'result-hood') is not None:

                # get the time of the post
                post_time = post.find('time', class_= 'result-date')
                post_datetime = post_time['datetime']

                # get the title and associated link
                post_title = post.find('a', class_='result-title hdrlnk')
                post_link = post_title['href']
                post_title_text = post_title.text

                # get the neighborhood
                post_hood = post.find('span', class_= 'result-hood').text

                # get the post price
                try:
                    post_price = int(post.a.text.strip().replace("$", ""))
                except ValueError:
                    continue

                # create dataframe of the post
                data = pd.DataFrame(
                    data={
                        "region": [location],
                        "post_datetime": [post_datetime],
                        "neighborhood": [post_hood],
                        "post_title_text": [post_title_text],
                        "post_price": [post_price],
                        "post_link": [post_link],
                    }
                )

                # append all-in dataframe
                all_apartments = all_apartments.append(data, sort=False)

    # format
    all_apartments['neighborhood'] = all_apartments['neighborhood'].str.translate(
        (str.maketrans({'(': '', ')': ''})))

    all_apartments['neighborhood'] = all_apartments['neighborhood'].str.lstrip()

    # create unique key
    all_apartments['post_datetime'] = pd.to_datetime(all_apartments['post_datetime'])
    #  all_apartments['temp'] = all_apartments['post_datetime'].dt.strftime("%Y_%m_%d")
    all_apartments['temp'] = datetime.today().strftime("%Y_%m_%d")
    all_apartments['id'] = all_apartments['post_link'].str.cat(all_apartments['temp'], sep="_")
    all_apartments = all_apartments.drop(columns=['temp'])

    return all_apartments


def update_data_records(all_rooms, all_apartments):
    """save to databases"""
    # apartment shares

    # update on amazon rds database
    database_path = os.environ['DATABASE_PATH']

    engine = create_engine(database_path)
    con = engine.connect()

    try:

        print('reading rds room share database... ')
        sql = ("""
        SELECT id, post_link FROM rooms
        """)
        x = pd.read_sql(sql, con=con)

        # drop any duplicate ids
        data = all_rooms.loc[~all_rooms['id'].isin(x['id'])]
        data = data.drop_duplicates(subset='id')
        # drop duplicate links
        data = data.loc[~data['post_link'].isin(x['post_link'])]

        if len(data) > 0:
            print(str(len(data)) + " new records will be added. ")
            data.to_sql('rooms', con=con, if_exists='append', index=False)

            print('\nCraigslist room share database successfully updated with '
                  + str(len(data)) + " new posts.")
        else:
            print('no new records to add.')

    #  except IntegrityError:
    except:
        print('error on apartment share sql append.')
        print('apartment share databases not updated.')

    # todo: repeat for full apartments

    try:

        print('reading rds apartment database... ')
        sql = ("""
        SELECT id, post_link FROM apartments
        """)
        x = pd.read_sql(sql, con=con)

        # drop any duplicate ids
        data = all_apartments.loc[~all_apartments['id'].isin(x['id'])]
        data = data.drop_duplicates(subset='id')
        # drop duplicate links
        data = data.loc[~data['post_link'].isin(x['post_link'])]

        if len(data) > 0:
            print(str(len(data)) + " new records will be added. ")
            data.to_sql('apartments', con=con, if_exists='append', index=False)

            print('\nCraigslist apartment database successfully updated with '
                  + str(len(data)) + " new posts.")
        else:
            print('no new records to add.')

    #  except IntegrityError:
    except:
        print('error on apartment share sql append.')
        print('apartment share databases not updated.')


def run_apartment_search():
    """"""
    searches = {
        "manhattan": "https://newyork.craigslist.org/search/mnh/roo?min_price=800",
        "brooklyn": "https://newyork.craigslist.org/search/brk/roo?min_price=800",
        "new_jersey": "https://newyork.craigslist.org/search/jsy/roo?min_price=800",
        "queens": "https://newyork.craigslist.org/search/que/roo?min_price=800",
        "bronx": "https://newyork.craigslist.org/search/brx/roo?min_price=800"
    }
    print('\nsearching for room shares...')
    all_rooms = get_apartment_data(searches)

    # repeat for full apartments
    apartment_searches = {
        "manhattan": "https://newyork.craigslist.org/search/mnh/apa?min_price=800",
        "brooklyn": "https://newyork.craigslist.org/search/brk/apa?min_price=800",
        "new_jersey": "https://newyork.craigslist.org/search/jsy/apa?min_price=800",
        "queens": "https://newyork.craigslist.org/search/que/apa?min_price=800",
        "bronx": "https://newyork.craigslist.org/search/brx/apa?min_price=800"
    }
    print('\nsearching for apartments...')
    all_apartments = get_apartment_data(apartment_searches)

    # update databases
    update_data_records(all_rooms, all_apartments)

    from time import strftime
    from datetime import datetime
    update = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    print('\ncraigslist apartment searches complete at ' + update)


if __name__ == '__main__':
    run_apartment_search()
