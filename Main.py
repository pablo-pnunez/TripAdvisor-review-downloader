# -*- coding: utf-8 -*-
from src.TripAdvisorRestaurants import TripAdvisorRestaurants
from src.TripAdvisorPOIs import TripAdvisorPOIs
import sys

def main():

    # ToDo: Cambiar la extensión de cada petición para evitar sobrecarga:
    # .nl, .dk, .at, .ru, .cn, .co.id, .co.kr, .co.za, .co.il

    # cities = ["Gijon", "Barcelona", "Warsaw", "Budapest", "Hamburg", "Vienna", "Bucharest", "New York City", "Paris", "Rome", "Madrid", "Berlin", "London"]
    # cities = ["Istanbul", "Moscow", "Saint Petersburg, Russia", "Athens"]
    cities = ["Gijon"]

    if len(sys.argv) > 1:
        cities = [sys.argv[1]]


    for city in cities:

        print(f"{'-'*50}\n{city}\n{'-'*50}")

        download_images = True
        download_hd_images = True

        tad_rst_obj = TripAdvisorRestaurants(city_query=city)
        tad_rst_obj.download_data(download_image_files=download_images, high_res_images=download_hd_images)

        # tad_poi_obj = TripAdvisorPOIs(city_query=city)
        # tad_poi_obj.download_data(download_image_files=download_images, high_res_images=download_hd_images)

if __name__ == "__main__":
    main()