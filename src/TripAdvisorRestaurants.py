from src.TripAdvisor import TripAdvisor, BlockAll

from pyquery import PyQuery
import pandas as pd
import numpy as np
import requests
import json
import math
import os
import re


class TripAdvisorRestaurants(TripAdvisor):
    
    def __init__(self, city, lang="en"):
        TripAdvisor.__init__(self, city=city, lang=lang)

    def download_data(self):
        '''Descarga todos los datos de una ciudad'''

        # 1. Download restaurants
        restaurants = self.download_restaurants()
        # 2. Download reviews
        reviews = self.download_reviews(restaurants)

    def get_restaurant_pages(self):
        '''Retorna el número de páginas de restaurantes'''
        url = f"https://www.tripadvisor.es/RestaurantSearch?Action=PAGE&ajax=1&availSearchEnabled=false&sortOrder=alphabetical&geo={self.geo_id}&o=a0"
        headers = {'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.111 Safari/537.36'}
        r = requests.get(url, headers=headers)
        pq = PyQuery(r.text)
        data = json.loads(pq.find('div.react-container.component-widget').attr("data-component-props"))
        data = math.ceil(data["listResultCount"]/30)
        return data

    def download_restaurants(self):
        '''Descarga todos los restaurantes'''

        file_path = f"{self.out_path}restaurants.pkl"

        if os.path.exists(file_path):
            print(f"The file {file_path} already exists, loading...")
            out_data = pd.read_pickle(file_path)
        else:
            num_pages = self.get_restaurant_pages()
            data = list(range(num_pages))
            results = self.parallelize_process(data=data, function=self.download_restaurants_from_page, desc=f"Restaurants from {self.city}")
            out_data = pd.DataFrame(sum(results,[]), columns=self.rest_cols)
            pd.to_pickle(out_data, file_path)
            print(f"{len(out_data)} items have been downloaded for the city of {self.city}")

        return out_data
       
    def download_reviews(self, restaurants):
        '''Descarga las reseñas a partir de los restaurantes'''
        file_path_reviews = f"{self.out_path}reviews.pkl"
        file_path_users = f"{self.out_path}users.pkl"

        if os.path.exists(file_path_reviews) and os.path.exists(file_path_users):
            print(f"The files already exists, loading...")
            out_data_reviews = pd.read_pickle(file_path_reviews)
            out_data_users = pd.read_pickle(file_path_users)
        else:
            results = self.parallelize_process(data=restaurants.values.tolist(), function=self.download_reviews_from_restaurant, desc=f"Reviews from {self.city}")
            res_reviews, res_users = list(zip(*results))

            out_data_reviews = pd.DataFrame(sum(res_reviews,[]), columns=self.review_cols)
            out_data_users = pd.DataFrame(sum(res_users,[]), columns=self.user_cols)
            out_data_users = out_data_users.drop_duplicates().sort_values("userId").reset_index(drop=True) # Eliminar duplicados

            pd.to_pickle(out_data_reviews, file_path_reviews)
            pd.to_pickle(out_data_users, file_path_users)

            print(f"{len(out_data_reviews)} reviews have been downloaded for the city of {self.city}")
            print(f"{len(out_data_users)} users have been downloaded for the city of {self.city}")

        return out_data
    
    def download_restaurants_from_page(self, page):
        '''Descarga los restaurantes de una página'''
        
        items_page = 30
        url = f"https://www.tripadvisor.com/RestaurantSearch?Action=PAGE&geo={self.geo_id}&sortOrder=alphabetical&o=a{page*items_page}&ajax=1"
        s = requests.Session()
        s.cookies.set_policy(BlockAll())
        r = s.get(url, headers=self.request_params)
        pq = PyQuery(r.text)

        rst_in_pg = pq("div[data-test-target='restaurants-list']")
        rsts = rst_in_pg("div[data-test$='_list_item']").not_("div[data-test^='SL']")

        if(len(rsts) == 0):
            print(f"Error getting items from: {url}")
            raise ValueError

        ret_data = []
        for r in rsts.items():
            name_url_item = r.find("a.Lwqic.Cj.b")
            name = ". ".join(name_url_item.text().split(". ")[1:])
            url = f'{self.base_url}{name_url_item.attr("href")}'
            id_r = int(re.findall(r"d(\d+)", url)[0])

            rating = r.find("svg[aria-label*='bubbles']")

            if len(rating) > 0:
                rating = int(rating.attr("aria-label").split(" of ")[0].replace(".", ""))
            else:
                rating = 0

            type_price = r.find("div.hBcUX.XFrjQ.mIBqD span.SUszq")

            type_r = []
            price = ""

            if len(type_price) == 2:
                type_r = type_price[0].text.split(", ")
                price = type_price[1].text
            elif len(type_price) == 1:
                if("$" in type_price[0].text):
                    price = type_price[0].text
                else:
                    type_r = type_price[0].text.split(", ")

            ret_data.append((id_r, name, self.city, price, url, rating, type_r))

        return ret_data

    def download_reviews_from_restaurant(self, restaurant):
        restaurant = dict(zip(self.rest_cols, restaurant))

        request_payload = "changeSet=REVIEW_LIST&filterLang=ALL"
        headersList = {
            "authority": "www.tripadvisor.com",
            "accept": "text/html, */*",
            "accept-language": "en-GB,en;q=0.9,en-US;q=0.8,es;q=0.7",
            "cache-control": "no-cache",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "origin": "https://www.tripadvisor.com",
            "referer": restaurant["url"],
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36 Edg/111.0.1661.51",
            "x-requested-with": "XMLHttpRequest" 
        }
        
        response = requests.request("POST", restaurant["url"], data=request_payload,  headers=headersList)
        pq = PyQuery(response.text)

        # Review number (all_langs)
        review_number = pq.find("span.reviews_header_count")
        review_number = 0 if len(review_number)==0 else int(re.findall(r"\d+\,*\d*",review_number.text().replace(",", ""))[0])

        reviews_per_page = 15
        reviews_pages = math.ceil(review_number/reviews_per_page)

        all_review_codes = []
        # For each page of comments
        for p in range(reviews_pages):
            page_url = restaurant["url"].replace("-Reviews-", f"-Reviews-or{p*reviews_per_page}-")
            response = requests.request("POST", page_url, data=request_payload,  headers=headersList)
            pq = PyQuery(response.text)

            page_reviews = pq.find("div.review-container")
            page_reviews = [PyQuery(r).attr("data-reviewid") for r in page_reviews]
            all_review_codes.extend(page_reviews)

        # Expand reviews: Se crean batches de 50 ids y se descarga la info ampliada de cada batch
        expand_url = "https://www.tripadvisor.com/OverlayWidgetAjax?Mode=EXPANDED_HOTEL_REVIEWS_RESP"
        review_batches = np.array_split(all_review_codes, max(1, review_number//50))
        
        all_reviews = []
        all_users = []

        for batch in review_batches:
            payload = f"reviews={'%2C'.join(batch)}&contextChoice=DETAIL&loadMtHeader=true"
            response = requests.request("POST", expand_url, data=payload,  headers=headersList)
            pq = PyQuery(f"<html><head></head><body>{response.text}</body></html>")

            for review in pq.find("body div[data-reviewlistingid]"):
                #Review info
                review = PyQuery(review)
                review.find("div.mgrRspnInline").remove() # Remove owner answers

                review_id = int(review.attr("data-reviewlistingid"))             

                review_title = review.find("div.quote").text()
                review_text = review.find("p.partial_entry").text()

                review_rating = int(re.search(r'bubble_(\d+)', review.find("span.ui_bubble_rating").attr("class")).group(1))
                review_url = f'{self.base_url}{review.find("div.quote a").attr("href")}'
                
                review_date = review.find("span.ratingDate").attr("title")
                review_date = pd.to_datetime(review_date , format='%B %d, %Y').date()

                review_lang = self.lang
                review_translation = review.find("div.prw_reviews_google_translate_button_hsx")
                if len(review_translation)>0: 
                    review_lang = re.search(r'sl=(\w+)', review_translation.find("span").attr("data-url")).group(1)

                review_images = list(set([img.attrib["src"] for img in review.find("div.photoContainer img")]))

                # User info
                user = review.find("div.member_info")
                
                user_id = -1
                if len(user.find("div.memberOverlayLink"))>0:
                    user_id = user.find("div.memberOverlayLink").attr("id").split("_")[1].split("-")[0]
                user_info = user.find("div.info_text").text().split("\n")
                user_name = user_info[0]
                user_loc = "" if len(user_info)==1 else user_info[1]

                all_reviews.append((review_id, user_id, restaurant["restaurantId"], review_title, review_text, review_date, review_rating, review_lang, review_images, review_url))
                all_users.append((user_id, user_name, user_loc))

        return all_reviews, all_users