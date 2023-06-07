# -*- coding: utf-8 -*-
from src.TripAdvisorRestaurants import TripAdvisorRestaurants
from src.TripAdvisorPOIs import TripAdvisorPOIs
import sys

def main():

    cities = ["Gijon", "Barcelona", "Warsaw", "Budapest", "Hamburg", "Vienna", "Bucharest", "New York City", "Paris", "Rome", "Madrid", "Berlin", "London"]
    # cities = ["Istanbul", "Moscow", "Saint Petersburg, Russia", "Athens"]

    cities = ["Lisboa"]

    if len(sys.argv) > 1:
        cities = [sys.argv[1]]

    for city in cities:

        print(f"{'-'*50}\n{city}\n{'-'*50}")        

        # tad_rst_obj = TripAdvisorRestaurants(city_query=city)
        # tad_rst_obj.download_data(download_image_files=False, high_res_images=False)

        tad_poi_obj = TripAdvisorPOIs(city_query=city)
        tad_poi_obj.download_data(download_image_files=False, high_res_images=False)

if __name__ == "__main__":
    main()