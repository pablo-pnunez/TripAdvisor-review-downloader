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
import time
import json
import sys
import cv2
import os
import re

import socks
import socket
import random


class TripAdvisor():
    base_url = "https://www.tripadvisor.com"
    review_cols = [
        "reviewId", "userId", "itemId", "title", "text", "date", "rating", 
        "language", "images", "url"]
    user_cols = ["userId", "name", "location"]


    def __init__(self, city_query, lang="en", category=""):
    
        self.city_query = city_query
        # self.proxy_list = self.__get_proxy_list__()

        self.geo_id, self.city = self.get_city_id_name()
        self.city_file_name = self.city.lower().replace(" ", "")

        self.lang = lang
        self.out_path = f"out/{self.city_file_name}/{category}/"

        os.makedirs(self.out_path, exist_ok=True)

        self.request_params = self.get_request_params()


    def __check_proxy__(self, proxy:str) -> str:
        """Función que comprueba la disponibilidad de una proxy para hacer 
        consultas a TripAdvisor. En el caso de que no responda en dos segundos, 
        se considera que el proxy no está disponible.

        Args:
            proxy (str): dirección ip del proxy.
        Returns:
            str: None si el proxy no está disponible, la dirección del proxy si 
                sí lo está.
        """        
        # user_info, proxy_info = proxy.split("//")[1].split("@")
        # username, password = user_info.split(":")
        # proxy_host, proxy_port = proxy_info.split(":")
        # socks.set_default_proxy(socks.SOCKS5, proxy_host, int(proxy_port), username=username, password=password)
        # socket.socket = socks.socksocket

        url = f"https://www.tripadvisor.es/TypeAheadJson?action=API&query={self.city_query}"
        headers = {
            "authority": "www.tripadvisor.es",
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-language": "es,en;q=0.9,ca;q=0.8",
            "cache-control": "no-cache",
            "cookie": "TADCID=1UPqdWPlu09b-EjjABQCXdElnkGETRW-Svh01l3nWnYOIj6okSgfmCuEPfZBu0TGR9KVzWaOzDL5acOTsbogAigeGOVSMM68qDU; TAUnique=%1%enc%3AUI4cdMFEA15Zy6l8XkIPIMnCFrHmfj6VGIToPozkk%2FIRJhIGgJrf%2FA%3D%3D; TASSK=enc%3AAPR2h99RYFszHUvVNy1crxMzgcucgeKc7mExJljvQpux6AbGTAZ0MnqrZy7iGDfAB21ev9b0zzkLttElAJdQM3srusq9b3gJZY9mfvMxeLpWmnZj9LWWsYFb%2BL7YGmRuYA%3D%3D; SRT=TART_SYNC; ServerPool=C; PMC=V2*MS.94*MD.20230608*LD.20230608; TART=%1%enc%3AWcupfF5CDyBozDGCZZB3leIOthAYtNTzIC7igATejNRVaBgeODxvueEcfKixqpV6OjRpONHHltE%3D; TATravelInfo=V2*A.2*MG.-1*HP.2*FL.3*RS.1; TASID=DB1E39A86DD64A9E82D2F0008421F009; PAC=AE2-m_quBnCu963U31X_ieRBPZI6qqD-saH6yIOVmYFCPmFuBCnvJ6P1rPleLfuVdoLSf44Q1l1fb1FZ143fJE_N8kTMKbM-4dLbzCqErnUSdQmmPA-iWzfV5xa_IsE1jdd_9a33cNKz117xX4o93qF9MD9bRKmfi5hmu7X1Iu0P; TAAUTHEAT=ksNs57W9TfJoJMvJABQCnPHiQaRASfmTxbKSWaoBQjXlIkq0ixkA41i4Vo_ctrKwj5KnWFdpW0j_Ylgl81eYgbNVlQaPUkuX7rtZMEqPxkdm1XeNX8aAszf8sjymWlJPXPd7OQH2ETzpQAEh7fnPUdHjsPjaYOBVTvCuWPsw4kMetC9Iucw2MHAQQCFAplxDYUHM2-QCXPnyOjtYhIyMODQtSAscarEWmO0; TASession=%1%V2ID.DB1E39A86DD64A9E82D2F0008421F009*SQ.3*PR.40185%7C*LS.RegistrationController*HS.recommended*ES.popularity*DS.5*SAS.popularity*FPS.oldFirst*TS.A154BA43833F18AA03D8C718F0608388*FA.1*DF.0*TRA.true*EAU._; TAUD=LA-1686225938887-1*RDD-1-2023_06_08*LG-1-2.1.F.*LD-2-.....; G_AUTH2_MIGRATION=informational; __vt=LbQQq4pRdlJM3t9SABQCwDrKuA05TCmUEEd0_4-PPCXrwu1Eo52JCei_1XaZ0mzlteeOUghb1HTghzQxEHNSc2WRDu93yp139wzmxctG3xZ4m6z7kZFDYtEKmadlprT6E4SJxqzo06ro-nfVdbOcoi9atD3mLcqfX-AS7JomG2Ofq1czH5Op3gWrvAZxeKAu2q9EIJ_7XSPqnnQR8pTrjRHlVPspWTj_qTztD-WHMkQYom1qp32DIj2G12PelmINC3GaKnQ31leLVxqitse5BtgeNCvgEXPpZQzaI_NOxnYHTV4PaYAd-Q; datadome=5wmJZNiVh80yasrWg-M64TVwJEWeIV05xpJndjKHmt8h9LWz-Ti9SkCydC0EIZ3xfPfZ4qx5S9uy9RxZa8JiTg_Ml9wRMdkgVAo5ZKMAcHa96PxrVmjg3TtCYZxna_Z0; OptanonConsent=isGpcEnabled=0&datestamp=Thu+Jun+08+2023+13%3A06%3A22+GMT%2B0100+(hora+de+verano+de+Europa+occidental)&version=202209.1.0&isIABGlobal=false&hosts=&consentId=b2ae457a-4d7d-46bc-8bf8-01d0fae6ab5a&interactionCount=1&landingPath=https%3A%2F%2Fwww.tripadvisor.de%2F&groups=C0001%3A1%2CC0002%3A0%2CC0003%3A0%2CC0004%3A0%2CSTACK42%3A0",
            "dnt": "1",
            "pragma": "no-cache",
            "referer": "https://www.tripadvisor.com/",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36" 
        }
        try:
            r = requests.get(url, headers=headers, proxies={"https":proxy}, timeout=2)
            return proxy
        except Exception as e:
            return None


    def __get_proxy_list__(self) -> list:
        """Función que extrae las direcciones ip de los proxies almacenadas en 
        en un fichero de texto en el que hay una dirección por línea y 
        selecciona solo aquellos proxies aptos para realizar queries a 
        TripAdvisor. Esto se hace en con ejecución paralela.

        Returns:
            list: direcciones ip de los proxies aptos.
        """
        alive = []
        with open("free_proxy.txt", "r") as f:
            proxies = f.read().splitlines()

        alive = self.parallelize_process(
            proxies, self.__check_proxy__, workers=len(proxies), 
            threads=True, desc="Proxy check")
        alive = [x for x in alive if x is not None]
        print(alive)
        return alive


    def get_proxy(self):
        # selected_proxy = np.random.choice(self.proxy_list)
        selected_proxy = "" # deshabilita el uso de proxies
        return {'https': selected_proxy}


    def get_city_id_name(self) -> tuple:
        """Función que obtiene el geoid de la ciudad que se desa scrappear. 
        Intenta la operación al menos tres veces.

        Returns:
            tuple: dupla de (geoid, código de respuesta http).
        """
        url = f"https://www.tripadvisor.com/TypeAheadJson?action=API&query={self.city_query}"
        headers = {
            "authority": "www.tripadvisor.com",
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-language": "es,en;q=0.9,ca;q=0.8",
            "cache-control": "no-cache",
            "dnt": "1",
            "pragma": "no-cache",
            "referer": "https://www.tripadvisor.com/",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36" 
        }

        max_retries = 3  # Número máximo de intentos
        retries = 0

        while retries < max_retries:
            try:
                r = requests.get(url, headers=headers, proxies=self.get_proxy())
                r.raise_for_status()  # Comprobar si la respuesta es exitosa
                response = json.loads(r.text)
                response = [r for r in response["results"] if r["type"]=="GEO"]
                geo_id = int(response[0]['value'])
                print(f"Selected city: {response[0]['name']} [{geo_id}]")
                return geo_id, response[0]["name"].split(", ")[0]
            except requests.exceptions.RequestException as e:
                retries += 1
                print(f"Request failed: {str(e)}. Retrying... ({retries}/{max_retries})")
                wait_time = random.randint(1, 5)  # Tiempo de espera aleatorio entre 1 y 5 segundos
                time.sleep(wait_time)
        
        print("Max retries exceeded. Unable to fetch city data.")
        exit()

    
    def get_request_params(self) -> dict:
        """Función que genera los parámetros necesarios para realizar un GET a
        TripAdvisor.

        Returns:
            dict: Diccionario con los prarámetros
        """
        
        url = f"https://www.tripadvisor.com/RestaurantSearch&geo={self.geo_id}"
        params = {'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.111 Safari/537.36', }

        r = requests.get(url, headers=params)
        # Se obtiene la cookie de sesión
        cookieDict = r.cookies.get_dict()
        cookieDict["TASession"] = cookieDict["TASession"] \
            .replace("TRA.true", "TRA.false")

        cookieDict = {
            # Se añade la cookie de identificación
            "TAUnique": "%1%enc%3AP4eDoHhGTx3dk0g9tT58cSIjdxMtLaGxvCpuHkLALKBcZDjTQsqGzA%3D%3D",
            "TASession": cookieDict["TASession"]}

        params["Cookie"] = ";".join(['%s=%s' % (name, value) for (name, value) in cookieDict.items()])
        params['cache-control'] = 'no-cache,no-store,must-revalidate'
        params["X-Requested-With"] = "XMLHttpRequest"
        return(params)
    

    # PASAR A DECORADOR. TIENE HERENCIA EN EL RESTO DE CLASES.
    def parallelize_process(
            self, data:list, function, workers:int=24, 
            threads:bool=True, desc:str="") -> list:
        """Función que paraleliza la ejecución de una función en bucle.

        Args:
            data (list): lista con los datos que recorre la función original
            function (function): función que se desea paralelizar
            workers (int, optional): número de hilos. Defaults to 24.
            threads (bool, optional): decide el tipo de clase a utilizar. 
                Defaults to True.
            desc (str, optional): parámetro tqdm. Defaults to "".

        Returns:
            list: resultados de la ejecución en paralelo.
        """
        workers = min(workers, len(data))

        if threads:  
            with ThreadPoolExecutor(max_workers=workers) as executor:
                # results = list(executor.map(function, data))
                results = list(
                    tqdm(
                        executor.map(function, data), 
                        total=len(data), 
                        desc=desc, 
                        file=sys.stdout
                    )
                )

        else:
            with Pool(processes=workers) as pool:
                # results = pool.map(self.download_restaurants_from_page, data)
                results = list(
                    tqdm(
                        pool.imap(function, data), 
                        total=len(data), 
                        desc=desc, 
                        file=sys.stdout
                    )
                )
        return results


    def download_data(
            self, download_image_files:bool=True, high_res_images:bool=True
            ) -> None:
        """Función que descarga todos los datos de una ciudad.

        Args:
            download_image_files (bool, optional): Defaults to True.
            high_res_images (bool, optional): Defaults to True.
        """

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


    def download_images(self, reviews:dict, high_res:bool=True) -> None:
        """Función de descarga de imágenes.

        Args:
            reviews (dict): diccionario con las reviews.
            high_res (bool, optional): Descarga de las imágenes en alta 
                resolución. Defaults to True.
        """
        # Solo reviews con foto
        reviews["n_images"] = reviews["images"].apply(lambda x: len(x))
        reviews = reviews.loc[reviews["n_images"]>0][["itemId", "reviewId", "images"]].sample(frac=1)
        # Crear carpeta de imágenes
        self.out_img_path = f"{self.out_path}images/"
        os.makedirs(self.out_img_path, exist_ok=True)
        # Método que descarga las fotos de una review
        self.parallelize_process(
            threads=True, workers=32 ,data=reviews.values.tolist(), 
            # partial fija un número de de parámetros de la antigua función, en
            # este caso el parámetro high_res, asociándola a una nueva función, 
            # en este caso function
            function=partial(self.download_images_from_review, high_res=high_res), 
            desc=f"Images from {self.city}")
    

    def download_images_from_review(
            self, review:list, high_res:bool=True) -> bool:
        """Función que descarga las imágenes específicas de una reveiew.

        Args:
            review (list): lista con el id del item, el id de la review y las
                imágenes de la review.
            high_res (bool, optional): Defaults to True.

        Returns:
            bool: Devuelve True si se ha ejecutado correctamente.
        """

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
                        # Ojo, posible bucle infinito
                        print(f"{img_path}\n{img_url}\n{exist}-{verified}", flush=True)
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
            new_url = re.sub(
                r"\/photo-(\w)\/", f"/photo-{nm}/", new_url, 0, re.MULTILINE)
            session = self.retry_session(retries=10)
            response = session.get(url=new_url, timeout=5)
            img_response = response.status_code
            img_content = response.content
            i+=1

        if i == len(possible_urls):
            print(f"\nERROR: {lowres_url}", flush=True)
            raise ValueError

        return new_url, img_content


    def retry_session(self, retries, session=None, backoff_factor=0.3):
        session = session or requests.Session()
        retry = Retry(
            total=retries,
            read=retries,
            connect=retries,
            backoff_factor=backoff_factor,
            # method_whitelist=False,
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
            payload = f"reviews={'%2C'.join(batch)}&contextChoice=DETAIL"
            response = requests.request("POST", expand_url, data=payload,  headers=headersList)
            pq = PyQuery(f"<html><head></head><body>{response.text}</body></html>")

            reviews = pq.find("body div[data-reviewlistingid]")
            # si no coincide suele ser por que la misma review aparece con 2 ids. Traducida y sin
            # assert len(reviews) == len(all_review_codes) 
            
            for rvidx, review in enumerate(reviews):
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