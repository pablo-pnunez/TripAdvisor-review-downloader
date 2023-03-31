# -*- coding: utf-8 -*-

import pandas as pd

from src.TripAdvisorRestaurants import TripAdvisorRestaurants
from src.TripAdvisorPOIs import TripAdvisorPOIs
from TripAdvisor import *
import sys

# -----------------------------------------------------------------------------------------------------------------------

def stepFour(CITY):

    n_threads = 24
    threads = []

    PATH = "/media/nas/pperez/data/TripAdvisor/" + CITY.lower().replace(" ", "") + "_data/"

    data = pd.read_pickle(PATH+"reviews.pkl")

    len_data = len(data)
    len_data_thread = len_data // n_threads

    for i in range(n_threads):

        data_from = i * len_data_thread
        data_to = (i + 1) * len_data_thread
        if (i == n_threads - 1):
            data_to = len_data
        data_thread = data.iloc[data_from:data_to, :].reset_index(drop=True)

        temp_thread = TripAdvisor(i, "Thread-" + str(i), i, city=CITY, data=data_thread, step=3)
        threads.append(temp_thread)
        threads[i].start()

# -----------------------------------------------------------------------------------------------------------------------

def main():

    cities = ["Gijon", "Barcelona", "Warsaw", "Budapest", "Hamburg", "Vienna", "Bucharest", "New York", "Paris", "Rome", "Madrid", "Berlin", "London"]
    cities = ["Istanbul", "Moscow", "Saint Petersburg, Russia", "Athens"]

    if len(sys.argv) > 1:
        cities = [sys.argv[1]]

    for city in cities:

        print("-"*50)        
        print(city)
        print("-"*50)

        tad_rst_obj = TripAdvisorRestaurants(city_query=city)
        tad_rst_obj.download_data()

        tad_poi_obj = TripAdvisorPOIs(city_query=city)
        tad_poi_obj.download_data()

        # 4. Download images
        # --------------------------------------------------------------------------
        # stepFour(CITY)


if __name__ == "__main__":
    main()