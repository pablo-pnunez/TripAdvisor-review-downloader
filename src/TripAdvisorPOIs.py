from src.TripAdvisor import TripAdvisor, BlockAll

from pyquery import PyQuery
from tqdm import tqdm
import pandas as pd
import numpy as np
import requests
import random
import shutil
import time
import json
import math
import os
import re


class TripAdvisorPOIs(TripAdvisor):
        
    item_cols = ['itemId', 'name', 'city', 'url', 'rating', 'categories', 'details']

    def __init__(self, city_query, lang="en"):
        TripAdvisor.__init__(self, city_query=city_query, lang=lang, category="pois")

        self.set_cookie = None
        self.session_ID = None

        self.temp_path = f"{self.out_path}/tmp/"
        os.makedirs(self.temp_path, exist_ok=True)

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
            results = self.parallelize_process(data=data, function=self.download_items_from_page, desc=f"Items from {self.city}")
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
            # items = items.loc[items["itemId"].isin([
            #    1752218, # Playa 
            #    1752244, # Termas
            #    9835963  # Plaza mayor
            #    ])]
            
            results = self.parallelize_process(threads=False, data=items.sample(frac=1).values.tolist(), function=self.download_reviews_from_item, desc=f"Reviews from {self.city}") #  workers=1, threads = True, 
            res_reviews, res_users = list(zip(*results))

            out_data_reviews = pd.DataFrame(sum(res_reviews,[]), columns=self.review_cols)
            out_data_users = pd.DataFrame(sum(res_users,[]), columns=self.user_cols)
            out_data_users = out_data_users.drop_duplicates().reset_index(drop=True) # Eliminar duplicados

            pd.to_pickle(out_data_reviews, file_path_reviews)
            pd.to_pickle(out_data_users, file_path_users)
            
        shutil.rmtree(self.temp_path)

        print(f"{len(out_data_reviews)} reviews found in {self.city}")
        print(f"{len(out_data_users)} users found in {self.city}")

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
            name = name_url_item.text().split("\n")[0]
            name = ". ".join(name.split(". ")[1:])
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
            category_detail = category_detail.split("\n")
            categories = category_detail[0].split(" • ")
            if len(category_detail)>1: details = category_detail[1] 

            ret_data.append((id_poi, name, self.city, url, rating, categories, details))

        return ret_data

    def get_review_data_from_url(self, item_id=None, update_token=None, language=None):
        
        if item_id is None: raise ValueError

        data = []

        extensions = ["com" ,  "es", "de", "pt" , "ru", "nl", "co.nz", "com.br"]
        extension = random.choice(extensions)

        reqUrl = f"https://www.tripadvisor.{extension}/data/graphql/ids"
        headersList = {
            "authority": f"www.tripadvisor.{extension}",
            "accept": "*/*",
            # "accept-language": "en-GB,en;q=0.9,en-US;q=0.8,es;q=0.7",
            "cache-control": "no-cache",
            "content-type": "application/json",
            "origin": f"https://www.tripadvisor.{extension}",
            "cookie": self.set_cookie,
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36 Edg/111.0.1661.54",
            "x-requested-by": "" 
        }

        language_data = [ { "inputKey": "language", "inputValues": [ language ] } ] if language is not None else []
   
        queries = ["b4a971da482f47170f67c2a1f81a2824"]# , "b1011c99a03ba78771a086be0d7d77ee"]  
        payload = json.dumps([ { "query": random.choice(queries), "variables": { 
                                "request": { 
                                    "routeParameters": { "contentType": "attraction", "contentId": str(item_id) }, 
                                    "clientState": { "userInput": language_data }, 
                                    "updateToken": update_token },
                                "currency": "EUR", 
                                "sessionId": self.session_ID,
                                "unitLength": "KILOMETERS" } } ])

        while len(data)==0:
            # time.sleep(random.randint(50,100)/100)
            response = requests.request("POST", reqUrl, data=payload,  headers=headersList)
            self.set_cookie = response.headers["set-cookie"]
            self.session_ID = [f for f in self.set_cookie.split(";") if "TASID" in f][0].split("TASID=")[-1]
            data = json.loads(response.text)[0]["data"]["Result"][0]["detailSectionGroups"]
            if len(data)==0: 
                print(f"Error downloading data, retrying...({item_id})")
                print("-"*50)
                print(response.text)
                print("-"*50)
                time.sleep(1)
        
        if language is None: data = [s for s in data if s["clusterId"]=="ReviewsAndQASection"]
       
        data = data[0]["detailSections"]
        data = [s for s in data if "tabs" in s.keys()][0]["tabs"][0]["content"]
                
        return data, headersList, payload

    def download_reviews_from_item(self, item_page):
        item_page = dict(zip(self.item_cols, item_page))
        item_id = item_page["itemId"]

        tmp_reviews_path = f"{self.temp_path}r_{item_id}.pkl"
        tmp_users_path = f"{self.temp_path}u_{item_id}.pkl"

        if os.path.exists(tmp_reviews_path) and os.path.exists(tmp_users_path):
            all_reviews = pd.read_pickle(tmp_reviews_path)
            all_users = pd.read_pickle(tmp_users_path)
        
        else:
            # Obtener los idiomas disponibles. Hay que ir uno por uno para evitar errores
            total_reviews = 0
            available_langs = []
            lang_data, _, _ = self.get_review_data_from_url(item_id)
            
            # Si hay datos
            if lang_data[0]["__typename"] !="WebPresentation_NoContentFallbackCard":
                # print(f"Retrying... {item_page['url']}", flush=True)
                # time.sleep(random.randint(100,300)/100)
                # lang_data = self.get_review_data_from_url(item_id)
                available_langs = [s for s in lang_data if s["__typename"]=="WebPresentation_ReviewsFilterCardWeb"][0]
                available_langs = available_langs["filterResponse"]["availableFilterGroups"]
                available_langs = [s for s in available_langs if s["__typename"]=="WebPresentation_SingleSelectFilterGroup" and s["filter"]["name"]=="language"][0]
                available_langs = {l["value"]:{"count":l["count"], "name":l["object"]["simpleText"]} for l in available_langs["filter"]["values"]}
                del available_langs["all"] # Eliminar All dado que no siempre funciona
            
                # print(available_langs)
                # available_langs = {"es":available_langs["es"]}

                total_reviews = sum([f["count"] for f in available_langs.values()])

            all_review_codes = []
            logs = []
            reviews_per_page = 10

            with tqdm(total=total_reviews, desc=f"Reviews from {item_page['name']})") as pbar:
                # Para cada idioma...
                for current_lang in available_langs:
                    updateToken = None
                    current_page = 0
                    total_pages = 1

                    retries = 0
                    start_lang_items = len(all_review_codes)

                    current_lang_expected_items = available_langs[current_lang]["count"]
                    current_lang_expected_pages = (current_lang_expected_items//reviews_per_page)+1
                    current_lang_downloaded_items = 0

                    while current_page<total_pages:
                        
                        data, data_headers, data_payload = self.get_review_data_from_url(item_id, updateToken, current_lang)
                        n_reviews = len([f for f in data if f["__typename"]=="WebPresentation_ReviewCardWeb"])
                        
                        # print(f"Item:{item_page['name']} Lang:{current_lang} Page:{current_page+1}/{total_pages} Data_rvs:{n_reviews}")

                        data_current_lang_expected_items = [f for f in data if f["__typename"]=="WebPresentation_PartialUpdatePaginationLinksListWeb"]
                        data_current_lang_expected_items = current_lang_expected_items if len(data_current_lang_expected_items)==0 else int(data_current_lang_expected_items[0]["totalResults"])
                        
                        """
                        E001 -> Si los items que esperamos para este idioma (petición inicial) no coinciden con los que retorna la petición del idioma.
                        E002 -> Si la petición retorna menos de 10 ítems para una página intermedia.
                        E003 -> Si la petición retorna un número de items no esperado para la última página.

                        """

                        if current_lang_expected_items!=data_current_lang_expected_items:
                            print(f"\n E001 [{current_lang}] -> {current_lang_expected_items}, {data_current_lang_expected_items}\t", flush=True)
                        
                        # Si no es la última página y no hay 10 elementos, algo falla:
                        if current_page!=(current_lang_expected_pages-1):
                            while n_reviews != reviews_per_page:
                                print(f"\nE002 [{item_page['name']}]", flush=True)
                                time.sleep(random.uniform(5, 10))
                                data, _, _ = self.get_review_data_from_url(item_id, updateToken, current_lang)
                                if data is not None: n_reviews = len([f for f in data if f["__typename"]=="WebPresentation_ReviewCardWeb"])


                        # Si es la última página y los elementos de data no coinciden con los que faltan, algo falla:
                        else:
                            while n_reviews!=(current_lang_expected_items-current_lang_downloaded_items):
                                print(f"\nE003 [{current_lang}] [{current_page}/{total_pages}] [{item_page['name']}] {n_reviews} ->  {current_lang_expected_items} {data_current_lang_expected_items} {current_lang_expected_items-current_lang_downloaded_items}", flush=True)
                                time.sleep(random.uniform(5, 10))
                                data, _, _ = self.get_review_data_from_url(item_id, updateToken, current_lang)
                                # ToDo: SI DATA ES NONE?
                                if data is not None: n_reviews = len([f for f in data if f["__typename"]=="WebPresentation_ReviewCardWeb"])

                        for item in data:

                            # Para cada review
                            if item["__typename"] == "WebPresentation_ReviewCardWeb":
                                review_id = str(json.loads(item["trackingKey"])["rid"])
                                # if review_id not in all_review_codes:
                                all_review_codes.append(review_id)
                                current_lang_downloaded_items+=1
                                pbar.update(1)
                                # else:
                                #     print(f"OJO, RESEÑA {review_id} REPETIDA!!!!!\n", flush=True)
                                # print(f"[{current_lang}]({current_page}/{total_pages}) -> {len(all_review_codes)}/{total_reviews}", flush=True)

                            # Para el item que informa sobre las páginas siguientes y anteriores
                            if item["__typename"] == "WebPresentation_PartialUpdatePaginationLinksListWeb":
                                current_page = int(item["currentPageNumber"])
                                page_tokens = { int(link["pageNumber"]):link["updateLink"]["updateToken"] for link in item["links"]}
                                total_pages = math.ceil(int(item["totalResults"])/reviews_per_page)# max(page_tokens.keys())

                                if current_page!=total_pages:
                                    updateToken = page_tokens[current_page+1]

                        # Si ya se han descargado todos los esperados para el idioma actual
                        if len(all_review_codes)-start_lang_items == current_lang_expected_items: 
                            current_page=total_pages
                        # Si no y no se encuentra el update token, retry (No se si pasa nunca)
                        elif not any(["WebPresentation_PartialUpdatePaginationLinksListWeb" in it["__typename"] for it in data]): 
                            print(f"\n{retries:02d} {item_page['name']} is retrying [lang:{current_lang} -> {len(all_review_codes)-start_lang_items}/{current_lang_expected_items}]\n", flush=True)# print(f'ERROR: {set([d["__typename"] for d in data])}')
                            time.sleep(1)
                            retries+=1
                        
                        
            # Expand reviews: Se crean batches de 50 ids y se descarga la info ampliada de cada batch
            all_reviews, all_users = self.expand_reviews_from_id(all_review_codes, item_page["url"])
            
            if (len(all_review_codes) != total_reviews):
                line = f"\n · {item_page['name']} downloaded ({len(all_reviews)} reviews & {len(all_review_codes)} codes & {total_reviews} expected)"
                logs.append(line)
                print(line, flush=True)
                exit()

            # Se guardan los datos del item temporalmente para reutilizar si se produce un error
            pd.to_pickle(all_reviews, tmp_reviews_path)
            pd.to_pickle(all_users, tmp_users_path)

            with open(f"logs_{self.city_file_name}.log", "a") as f:
                f.writelines(logs)

        return all_reviews, all_users