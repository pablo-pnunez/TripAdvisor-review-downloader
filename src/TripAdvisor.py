import os
import json
import requests

from tqdm import tqdm
from http import cookiejar
from multiprocessing import Pool
from concurrent.futures import ThreadPoolExecutor

class TripAdvisor():
    
    base_url = "https://www.tripadvisor.com"
    rest_cols = ["restaurantId", "name", "city", "priceInterval", "url", "rating", "type"]
    review_cols = ["reviewId", "userId", "restaurantId", "title", "text", "date", "rating", "language", "images", "url"]
    user_cols = ["userId", "name", "location"]

    def __init__(self, city, lang="en", category=""):
    
        self.city = city
        self.city_file_name = self.city.lower().replace(" ", "")

        self.lang = lang
        self.out_path = f"out/{self.city_file_name}/{category}/"

        os.makedirs(self.out_path, exist_ok=True)

        self.geo_id = self.get_geo_id()
        self.request_params = self.get_request_params()

    def get_geo_id(self):
        url = f"https://www.tripadvisor.com/TypeAheadJson?action=API&query={self.city}"
        headers = {'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.111 Safari/537.36'}
        r = requests.get(url, headers=headers)
        response = json.loads(r.text)
        id = int(response['results'][0]['value'])
        return id
    
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
    
    def parallelize_process(self, data, function, workers=15, threads=False, desc=""):

        workers = min(workers, len(data))

        if threads:  
            with ThreadPoolExecutor(max_workers=workers) as executor:
                # results = list(executor.map(function, data))
                results = list(tqdm(executor.map(function, data), total=len(data), desc=desc))

        else:
            with Pool(processes=workers) as pool:
                # results = pool.map(self.download_restaurants_from_page, data)
                results = list(tqdm(pool.imap(function, data), total=len(data), desc=desc))
        
        return results


class BlockAll(cookiejar.CookiePolicy):
    return_ok = set_ok = domain_return_ok = path_return_ok = lambda self, *args, **kwargs: False
    netscape = True
    rfc2965 = hide_cookie2 = False