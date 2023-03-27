from src.TripAdvisor import TripAdvisor, BlockAll

from pyquery import PyQuery
import pandas as pd
import numpy as np
import requests
import json
import math
import os
import re


class TripAdvisorPOIs(TripAdvisor):
    
    review_cols = ["reviewId", "username", "restaurantId", "title", "text", "date", "rating", "language", "images", "url"]
    item_cols = ["itemId", "name", "city", "url", "rating", "categories", "details"]
    user_cols = ["username", "name", "location"]

    def __init__(self, city, lang="en"):
        TripAdvisor.__init__(self, city=city, lang=lang, category="pois")

    def download_data(self):
        '''Descarga todos los datos de una ciudad'''

        # 1. Download restaurants
        items = self.download_items()
        # 2. Download reviews
        reviews = self.download_reviews(items)

    def get_item_pages(self):
        '''Retorna el número de páginas de items'''
        url = f"https://www.tripadvisor.com/Attractions-g{self.geo_id}-oa0-Activities.html"
        headers = {'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.111 Safari/537.36'}
        r = requests.get(url, headers=headers)
        pq = PyQuery(r.text)
        data = int(pq.find("section[data-automation='WebPresentation_PaginationLinksList']").text().split(" of ")[-1].replace(",", ""))
        data = math.ceil(data/30)
        return data

    def download_items(self):
        '''Descarga todos los items'''

        file_path = f"{self.out_path}items.pkl"

        if os.path.exists(file_path):
            print(f"The file {file_path} already exists, loading...")
            out_data = pd.read_pickle(file_path)
        else:
            num_pages = self.get_item_pages()
            data = list(range(num_pages))
            results = self.parallelize_process( data=data, function=self.download_items_from_page, desc=f"Items from {self.city}")
            out_data = pd.DataFrame(sum(results,[]), columns=self.item_cols)
            pd.to_pickle(out_data, file_path)
        
        print(f"{len(out_data)} items found in {self.city}")

        return out_data
       
    def download_reviews(self, items):
        '''Descarga las reseñas a partir de los restaurantes'''
        file_path_reviews = f"{self.out_path}reviews.pkl"
        file_path_users = f"{self.out_path}users.pkl"

        if os.path.exists(file_path_reviews) and os.path.exists(file_path_users):
            print(f"The files already exists, loading...")
            out_data_reviews = pd.read_pickle(file_path_reviews)
            out_data_users = pd.read_pickle(file_path_users)
        else:
            results = self.parallelize_process(threads=True ,data=items.values.tolist(), function=self.download_reviews_from_item, desc=f"Reviews from {self.city}")
            res_reviews, res_users = list(zip(*results))

            out_data_reviews = pd.DataFrame(sum(res_reviews,[]), columns=self.review_cols)
            out_data_users = pd.DataFrame(sum(res_users,[]), columns=self.user_cols)
            out_data_users = out_data_users.drop_duplicates().reset_index(drop=True) # Eliminar duplicados

            pd.to_pickle(out_data_reviews, file_path_reviews)
            pd.to_pickle(out_data_users, file_path_users)

            print(f"{len(out_data_reviews)} reviews have been downloaded for the city of {self.city}")
            print(f"{len(out_data_users)} users have been downloaded for the city of {self.city}")

        return out_data_reviews, out_data_users
    
    def download_items_from_page(self, page):
        '''Descarga los items de una página'''
        
        items_page = 30
        url = f"https://www.tripadvisor.com/Attractions-g{self.geo_id}-oa{page*items_page}-Activities.html"
        s = requests.Session()
        s.cookies.set_policy(BlockAll())
        r = s.get(url, headers=self.request_params)
        pq = PyQuery(r.text)

        itms = pq.find("div[data-part='ListSections'] section[data-automation='WebPresentation_SingleFlexCardSection']")

        if(len(itms) == 0):
            print(f"Error getting items from: {url}")
            raise ValueError

        ret_data = []
        for itm in itms.items():
            name_url_item = itm.find("header.VLKGO")
            name = ". ".join(name_url_item.find("span.title").text().split(". ")[1:])
            url = f'{self.base_url}{name_url_item.find("a").attr("href")}'
            id_poi = int(re.findall(r"d(\d+)", url)[0])

            rating = itm.find("svg[aria-label*='bubbles']")

            if len(rating) > 0:
                rating = int(rating.attr("aria-label").split(" of ")[0].replace(".", ""))
            else:
                rating = 0

            category_detail = itm.find("div.alPVI.eNNhq.PgLKC.tnGGX.yzLvM").text()
            details = ""
            categories = []
            if "\n" in category_detail:
                category_detail = category_detail.split("\n")
                categories = category_detail[0].split(" • ")
                details = category_detail[1]

            ret_data.append((id_poi, name, self.city, url, rating, categories, details))

        return ret_data

    def download_reviews_from_item(self, item_page):
        item_page = dict(zip(self.item_cols, item_page))
        item_id = item_page["itemId"]

        all_reviews = []
        all_users = []
        
        reqUrl = "https://www.tripadvisor.com/data/graphql/ids"
        
        headersList = {
            "authority": "www.tripadvisor.com",
            "accept": "*/*",
            "accept-language": "en-GB,en;q=0.9,en-US;q=0.8,es;q=0.7",
            "cache-control": "no-cache",
            "content-type": "application/json",
            "origin": "https://www.tripadvisor.com",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36 Edg/111.0.1661.54",
            "x-requested-by": "" 
        }

        # Primero obtenemos los lenguajes disponibles
        updateToken = None
        payload = json.dumps([ { "query": "f537d248719065257f43323534d737e8", "variables": { "request": { 
                                    "routeParameters": { "contentType": "attraction", "contentId": str(item_id) }, 
                                    "clientState": { "userInput": [ { "inputKey": "language", "inputValues": [ "all" ] } ] }, 
                                    "updateToken": updateToken }, "currency": "USD", "unitLength": "MILES" } } ])

        response = requests.request("POST", reqUrl, data=payload,  headers=headersList)
        data = json.loads(response.text)[0]["data"]["Result"][0]["detailSectionGroups"][0]["detailSections"][0]["tabs"][0]["content"]
        filter_lang_idx = np.argmax(["ReviewsFilterCardWeb" in it["__typename"] for it in data])
        filters = data[filter_lang_idx]["filterResponse"]["availableFilterGroups"]
        lang_idx = np.argmax(["language" in f["name"] for f in filters])
        languages = [f["value"] for f in filters[lang_idx]["filter"]["values"]]
        languages.remove("all")

        for current_lang in languages:
            # Luego, para cada lenguaje, descargamos las reviews
            updateToken = None
            current_page = 0
            total_pages = 1

            while current_page<total_pages:

                payload = json.dumps([ { "query": "f537d248719065257f43323534d737e8", "variables": { "request": { 
                                        "routeParameters": { "contentType": "attraction", "contentId": str(item_id) }, 
                                        "clientState": { "userInput": [ { "inputKey": "language", "inputValues": [ current_lang ] } ] }, 
                                        "updateToken": updateToken }, "currency": "USD", "unitLength": "MILES" } } ])

                response = requests.request("POST", reqUrl, data=payload,  headers=headersList)
                data = json.loads(response.text)[0]["data"]["Result"][0]["detailSectionGroups"][0]["detailSections"][0]["tabs"][0]["content"]

                for item in data:

                    # Para cada review
                    if item["__typename"] == "WebPresentation_ReviewCardWeb":
                        review_id = json.loads(item["trackingKey"])["rid"]
                        review_title = item["htmlTitle"]["text"]
                        review_text = item["htmlText"]["text"]
                        review_rating = item["bubbleRatingNumber"]*10
                        review_url = f'{self.base_url}{item["cardLink"]["webRoute"]["webLinkUrl"]}'

                        review_lang = current_lang

                        review_images = []
                        if item["photos"] is not None:
                            review_images = [f["photo"]["photoSizes"] for f in item["photos"]]
                        
                        review_date = item["publishedDate"]["text"].replace("Written ", "")
                        review_date = pd.to_datetime(review_date , format='%B %d, %Y').date()

                        user_name = item["userProfile"]["displayName"]
                        user_account = item["userProfile"]["profileRoute"]
                        if user_account is not None: user_account = user_account["url"].split("/")[-1]
                        user_location = item["userProfile"]["hometown"]

                        all_reviews.append((review_id, user_account, item_page["itemId"], review_title, review_text, review_date, review_rating, review_lang, review_images, review_url))
                        all_users.append((user_account, user_name, user_location))

                    # Para el item que informa sobre las páginas siguientes y anteriores
                    if item["__typename"] == "WebPresentation_PartialUpdatePaginationLinksListWeb":
                        current_page = int(item["currentPageNumber"])
                        page_tokens = { int(link["pageNumber"]):link["updateLink"]["updateToken"] for link in item["links"]}
                        total_pages = max(page_tokens.keys())

                        if current_page!=total_pages:
                            updateToken = page_tokens[current_page+1]

                # Si no hay más que una página
                if not any(["WebPresentation_PartialUpdatePaginationLinksListWeb" in it["__typename"] for it in data]):
                    current_page=total_pages

        return all_reviews, all_users