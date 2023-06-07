from concurrent.futures import ThreadPoolExecutor
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from multiprocessing import Pool
from functools import partial
from pyquery import PyQuery
from http import cookiejar
from tqdm import tqdm
import pandas as pd
import numpy as np
import requests
import json
import sys
import cv2
import os
import re


class TripAdvisor():
    
    base_url = "https://www.tripadvisor.com"

    review_cols = ["reviewId", "userId", "itemId", "title", "text", "date", "rating", "language", "images", "url"]
    user_cols = ["userId", "name", "location"]

    def __init__(self, city_query, lang="en", category=""):
    
        self.city_query = city_query
        self.geo_id, self.city = self.get_city_id_name()

        self.city_file_name = self.city.lower().replace(" ", "")

        self.lang = lang
        self.out_path = f"out/{self.city_file_name}/{category}/"

        os.makedirs(self.out_path, exist_ok=True)

        self.request_params = self.get_request_params()

    def get_city_id_name(self):
        url = f"https://www.tripadvisor.com/TypeAheadJson?action=API&query={self.city_query}"
        headers = {'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.111 Safari/537.36'}
        r = requests.get(url, headers=headers)
        response = json.loads(r.text)
        response = [r for r in response["results"] if r["type"]=="GEO"]
        geo_id = int(response[0]['value'])
        
        print(f"Selected city: {response[0]['name']} [{geo_id}]")

        return geo_id, response[0]["name"].split(", ")[0]
    
    def get_request_params(self):

        url = f"https://www.tripadvisor.com/RestaurantSearch&geo={self.geo_id}"
        params = {'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.111 Safari/537.36', }

        r = requests.get(url, headers=params)

        cookieDict = r.cookies.get_dict()
        cookieDict["TASession"] = cookieDict["TASession"].replace("TRA.true", "TRA.false")

        cookieDict = {"TAUnique": "%1%enc%3AP4eDoHhGTx3dk0g9tT58cSIjdxMtLaGxvCpuHkLALKBcZDjTQsqGzA%3D%3D",
                      "TASession": cookieDict["TASession"]}

        params["Cookie"] = ";".join(['%s=%s' % (name, value) for (name, value) in cookieDict.items()])
        params['cache-control'] = 'no-cache,no-store,must-revalidate'
        params["X-Requested-With"] = "XMLHttpRequest"
        return(params)
    
    def parallelize_process(self, data, function, workers=24, threads=False, desc=""):

        workers = min(workers, len(data))

        if threads:  
            with ThreadPoolExecutor(max_workers=workers) as executor:
                # results = list(executor.map(function, data))
                results = list(tqdm(executor.map(function, data), total=len(data), desc=desc, file=sys.stdout))

        else:
            with Pool(processes=workers) as pool:
                # results = pool.map(self.download_restaurants_from_page, data)
                results = list(tqdm(pool.imap(function, data), total=len(data), desc=desc, file=sys.stdout))

        return results

    def download_data(self, download_image_files=True, high_res_images=True):
        '''Descarga todos los datos de una ciudad'''

        # 1. Download restaurants
        items = self.download_items()
        # 2. Download reviews
        reviews = self.download_reviews(items)
        # 3. Download images?
        if download_image_files:
            self.download_images(reviews[0], high_res=high_res_images)

    def download_items(self):
        raise NotImplemented

    def download_reviews(self, items):
        raise NotImplemented

    def download_images(self, reviews, high_res=True):
        # Solo reviews con foto
        reviews["n_images"] = reviews["images"].apply(lambda x: len(x))
        reviews = reviews.loc[reviews["n_images"]>0][["itemId", "reviewId", "images"]]
        # Crear carpeta de imágenes
        self.out_img_path = f"{self.out_path}images/"
        os.makedirs(self.out_img_path, exist_ok=True)
        # Método que descarga las fotos de una review
        self.parallelize_process(threads=True, workers=32 ,data=reviews.values.tolist(), function=partial(self.download_images_from_review, high_res=high_res), desc=f"Images from {self.city}")
    
    def download_images_from_review(self, review, high_res=True):
        item_id = review[0]
        review_id = review[1]
        images = review[2]

        img_content = None

        review_path = f"{self.out_img_path}{'hd' if high_res else 'sd'}/{item_id}/{review_id}/"
        os.makedirs(review_path, exist_ok=True)

        for idx_img, img_url in enumerate(images):
            img_path = f"{review_path}{idx_img:04d}.jpg"
            
            exist = os.path.exists(img_path)
            verified = False

            while not exist or not verified:

                if not exist:
                    if high_res:
                        img_url, img_content = self.image_url_to_highres(img_url)
                    else:
                        session = self.retry_session(retries=10)
                        response = session.get(url=img_url, timeout=5)
                        img_content = response.content

                    with open(img_path, "wb") as f:
                        f.write(img_content)

                    exist = os.path.exists(img_path)        

                if exist and not verified:
                    try:
                        img = cv2.imread(img_path)
                        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                        verified = True
                    except Exception as e:
                        print(img_path, flush=True)
                        os.remove(img_path)
                
        return True

    def image_url_to_highres(self, lowres_url):
        possible_urls = ["o", "w", "m", "p", "s", "i", "f", "l", "t"]
        img_content = None
        img_response = 404

        new_url = lowres_url
        i = 0

        while i < len(possible_urls) and img_response!=200:
            nm = possible_urls[i]
            new_url = re.sub(r"photo-(\w)", f"photo-{nm}", new_url, 0, re.MULTILINE)
            session = self.retry_session(retries=10)
            response = session.get(url=new_url, timeout=5)
            img_response = response.status_code
            img_content = response.content
            i+=1

        if i == len(possible_urls):
            print(lowres_url, flush=True)
            raise ValueError

        return new_url, img_content

    def retry_session(self, retries, session=None, backoff_factor=0.3):
        session = session or requests.Session()
        retry = Retry(
            total=retries,
            read=retries,
            connect=retries,
            backoff_factor=backoff_factor,
            method_whitelist=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        return session

    def expand_reviews_from_id(self, all_review_codes, item_url, batch_size=50):

        ''' Expand reviews: Se crean batches de 50 ids y se descarga la info ampliada de cada batch'''
        
        expand_url = "https://www.tripadvisor.com/OverlayWidgetAjax?Mode=EXPANDED_HOTEL_REVIEWS_RESP"
        headersList = {
            "authority": self.base_url,
            "accept": "text/html, */*",
            "accept-language": "en-GB,en;q=0.9,en-US;q=0.8,es;q=0.7",
            "cache-control": "no-cache",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "origin": self.base_url,
            "referer": item_url,
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36 Edg/111.0.1661.51",
            "x-requested-with": "XMLHttpRequest" 
        }

        review_batches = np.array_split(all_review_codes, max(1, len(all_review_codes)//batch_size))
        
        item_id = int(re.findall(r"d(\d+)",item_url)[0])

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


                all_reviews.append((review_id, user_id, item_id, review_title, review_text, review_date, review_rating, review_lang, review_images, review_url))
                all_users.append((user_id, user_name, user_loc))
        
        return all_reviews, all_users


class BlockAll(cookiejar.CookiePolicy):
    return_ok = set_ok = domain_return_ok = path_return_ok = lambda self, *args, **kwargs: False
    netscape = True
    rfc2965 = hide_cookie2 = False