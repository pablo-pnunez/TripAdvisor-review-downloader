# -*- coding: utf-8 -*-
from src.TripAdvisorRestaurants import TripAdvisorRestaurants
from src.TripAdvisorPOIs import TripAdvisorPOIs
from TripAdvisor import *
import sys

def main():

    cities = ["Gijon", "Barcelona", "Warsaw", "Budapest", "Hamburg", "Vienna", "Bucharest", "New York", "Paris", "Rome", "Madrid", "Berlin", "London"]
    cities = ["Istanbul", "Moscow", "Saint Petersburg, Russia", "Athens"]

    cities = ["Boal, asturias"]

    if len(sys.argv) > 1:
        cities = [sys.argv[1]]

    for city in cities:

        print("-"*50)        
        print(city)
        print("-"*50)

        tad_rst_obj = TripAdvisorRestaurants(city_query=city)
        tad_rst_obj.download_data(download_image_files=True)

if __name__ == "__main__":
    main()