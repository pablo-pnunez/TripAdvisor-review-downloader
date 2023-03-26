# -*- coding: utf-8 -*-

import pandas as pd

from src.TripAdvisorRestaurants import TripAdvisorRestaurants
from TripAdvisor import *

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

def getStats(CITY):

    FOLDER = "/media/nas/pperez/data/TripAdvisor/%s_data/" % CITY.lower()
    IMG_FOLDER = FOLDER + "images/"

    RST = pd.read_pickle(FOLDER + "restaurants.pkl")
    USRS = pd.read_pickle(FOLDER + "users.pkl")
    RVW = pd.read_pickle(FOLDER + "reviews.pkl")

    # Add columns with number of images and likes
    RVW["num_images"] = RVW.images.apply(lambda x: len(x))
    RVW["like"] = RVW.rating.apply(lambda x: 1 if x > 30 else 0)
    RVW["restaurantId"] = RVW.restaurantId.astype(int)

    # Add columns for restaurants
    RST["id"] = RST.id.astype(int)
    RST["reviews"] = 0

    print("Retaurantes: " + str(len(RST.id.unique())))
    print("Usuarios: " + str(len(USRS.loc[(USRS.id != "")])))
    print("Reviews: " + str(len(RVW.loc[(RVW.userId != "")])))
    print("Imágenes: " + str(sum(RVW.num_images)))
    print("")

    # Keep the ones with images
    RVW = RVW.loc[RVW.num_images > 0]

    # For each restaurant
    # for i, r in RVW.groupby("restaurantId"):
    #     likes = (sum(r.like) * 100) / len(r)
    #     RST.loc[RST.id == i, ["like_prop", "reviews"]] = likes, len(r)

    # Stay with those who have reviews with images
    RST = RST.loc[RST.reviews > 0]

    print("Restaurantes (con imágen): ", len(RST))
    print("Usuarios (con imágen): ", len(RVW.userId.unique()))
    print("Reviews (con imágen): ", len(RVW))
    print("")
    print("Porcentaje de likes: ", sum(RVW.like)/len(RVW)*100)

    RET = pd.DataFrame(columns=['user', 'likes', 'reviews'])

    for i, g in RVW.groupby("userId"):
        likes = sum(g.like)
        total = int(len(g))
        RET = RET.append({"user": i, "likes": likes, "reviews": total}, ignore_index=True)

    RET.to_csv("../../stats/user_stats_"+CITY.lower()+".csv")

# -----------------------------------------------------------------------------------------------------------------------

def main():

    cities = ["London", "Berlin", "Madrid", "Rome", "Paris", "Bucharest", "Vienna", "Hamburg", "Budapest", "Warsaw"]

    cities = ["Gijon"]

    for city in cities:

        tad_obj = TripAdvisorRestaurants(city=city)
        tad_obj.download_data()

        # 4. Download images
        # --------------------------------------------------------------------------
        # stepFour(CITY)


        # Obtain stats
        # getStats(CITY)


if __name__ == "__main__":
    main()