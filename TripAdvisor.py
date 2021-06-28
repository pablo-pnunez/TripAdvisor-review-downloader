# -*- coding: utf-8 -*-

import pandas as pd
import threading
import time
import requests
from time import sleep

from tqdm import tqdm
import ssl
from pyquery import PyQuery
import urllib.request
import urllib
import re
import os
import json
from http import cookiejar
import filetype
import cv2
from PIL import Image

class BlockAll(cookiejar.CookiePolicy):
    return_ok = set_ok = domain_return_ok = path_return_ok = lambda self, *args, **kwargs: False
    netscape = True
    rfc2965 = hide_cookie2 = False

class TripAdvisorHelper():

    def __init__(self):
        pd.set_option('display.max_rows', 20)
        pd.set_option('display.max_columns', 500)
        pd.set_option('display.width', 1000)

    def joinReviews(self,CITY):

        revs = []
        #usrs = pd.DataFrame(columns=TripAdvisor.user_cols)

        tmp_folder = TripAdvisor.TMP_FOLDER+"/"+CITY.lower()

        for f in os.listdir(tmp_folder):

            if(("reviews" in f) and (".pkl" in f)):
                tmp_rev = pd.read_pickle(tmp_folder+"/"+f)
                #revs = revs.append(tmp_rev,ignore_index=True)
                if(len(tmp_rev)>0):revs.extend(tmp_rev.values.tolist())

        #usrs = usrs.drop_duplicates("id")
        revs = pd.DataFrame(revs)
        revs.columns = tmp_rev.columns
        revs = revs.drop_duplicates("reviewId")

        #if(len(usrs)>0):pd.to_pickle(usrs,"users.pkl")
        if(len(revs)>0):pd.to_pickle(revs,"revIDS-"+CITY.lower().replace(" ","")+".pkl")

        #Eliminar los ficheros de la carpeta.
        for f in os.listdir(tmp_folder):
            if(("reviews-" in f)  and (".pkl" in f)):
                os.remove(tmp_folder+"/"+f)

    def joinAndAppendFiles(self,CITY):

        revs = []
        usrs = []

        tmp_folder = TripAdvisor.TMP_FOLDER+"/"+CITY.lower()

        for f in os.listdir(tmp_folder):
            if(".pkl" in f):
                tmp = pd.read_pickle(tmp_folder + "/" + f)
                tmp = tmp.values.tolist()
                if("reviews-" in f):revs.extend(tmp)
                elif("users-" in f):usrs.extend(tmp)

        revs = pd.DataFrame(revs)
        revs.columns = TripAdvisor.review_cols
        revs = revs.drop_duplicates("reviewId")

        usrs = pd.DataFrame(usrs)
        usrs.columns = TripAdvisor.user_cols
        usrs = usrs.drop_duplicates("id")

        pd.to_pickle(revs,"reviews-"+CITY.lower().replace(" ","")+".pkl")
        pd.to_pickle(usrs,"users-"+CITY.lower().replace(" ","")+".pkl")

        # Eliminar los ficheros de la carpeta.
        for f in os.listdir(TripAdvisor.TMP_FOLDER):
            if((".pkl" in f) and(("reviews-" in f) or ("users-" in f))):
                os.remove(tmp_folder + "/" + f)

        os.remove("revIDS-"+CITY.lower().replace(" ","")+".pkl")

    def joinRestaurants(self, CITY):

        #rest = pd.DataFrame(columns=TripAdvisor.rest_cols)
        rest = []

        tmp_folder = TripAdvisor.TMP_FOLDER+"/"+CITY.lower()

        for f in os.listdir(tmp_folder):

            if (("restaurants-" in f) and (".pkl" in f)):
                tmp_rest = pd.read_pickle(tmp_folder + "/" + f)
                if(len(tmp_rest)>0):rest.extend(tmp_rest.values.tolist())
                #rest = rest.append(tmp_rest, ignore_index=True)

        rest = pd.DataFrame(rest)
        rest.columns = TripAdvisor.rest_cols

        if (len(rest) > 0):
            rest = rest.drop_duplicates("id")
            pd.to_pickle(rest, "restaurants-"+CITY.lower().replace(" ","")+".pkl")

        # Eliminar los ficheros de la carpeta.
        for f in os.listdir(tmp_folder):
            if (("restaurants-" in f) and (".pkl" in f)):
                os.remove(tmp_folder + "/" + f)

    def getRestaurantPages(self,CITY):
        # url = "https://www.tripadvisor.com/RestaurantSearch?Action=PAGE&geo=" + str(self.getGeoId(CITY)) + "&sortOrder=alphabetical"
        url = "https://www.tripadvisor.es/RestaurantSearch?Action=PAGE&ajax=1&availSearchEnabled=false&sortOrder=alphabetical&geo=%s&o=a0" % str(self.getGeoId(CITY))
        headers = { 'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.111 Safari/537.36', }
        r = requests.get(url, headers=headers)
        pq = PyQuery(r.text)
        data = json.loads(pq.find("div#component_39").attr("data-component-props"))
        data = data["listResultCount"]//30
        return data

    def getGeoId(self, CITY):
        url = "https://www.tripadvisor.com/TypeAheadJson?action=API&query=" + CITY
        headers = { 'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.111 Safari/537.36', }
        r = requests.get(url, headers=headers)
        response = json.loads(r.text)
        id = int(response['results'][0]['value'])

        return id

class TripAdvisor(threading.Thread):

    TMP_FOLDER = "tmp_data"
    BASE_URL = "https://www.tripadvisor.com"
    RESTAURANTS_URL = BASE_URL+"/Restaurants"
    GEO_ID = 0
    SUCCESS_TAG = 200

    CITY = None
    DATA = None
    STEP = None
    ITEMS = None

    rest_cols = ["id","name","city","priceInterval","url","rating","type"]
    review_cols = ["reviewId", "userId", "restaurantId", "title", "text", "date", "rating", "language", "images", "url"]
    user_cols = ["id", "name", "location"]

    def __init__(self, threadID, name, counter,city = "Barcelona", data = None, step=1, lang="es"):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.counter = counter

        self.LANG = lang
        self.CITY = city
        self.PATH = "/media/nas/pperez/data/TripAdvisor/" + city.lower().replace(" ","") + "_data/"

        self.TMP_FOLDER = self.TMP_FOLDER+"/"+city.lower()
        os.makedirs(self.TMP_FOLDER,exist_ok=True)

        self.GEO_ID = TripAdvisorHelper().getGeoId(CITY=city)
        self.PARAMS = self.getParams()

        self.DATA = data
        self.STEP = step
        if(data is None):self.ITEMS = len(data)

        pd.set_option('display.max_rows', 10)
        pd.set_option('display.max_columns', 500)
        pd.set_option('display.width', 1000)

    def run(self):
        print("Starting " + self.name)

        #Descargar lista de restaurantes...
        if(self.STEP==0):
            self.downloadRestaurants()
        #Descargar reviews...
        elif(self.STEP==1):
            self.downloadReviewData()

        #Completar reviews...
        elif(self.STEP==2):
            self.completeReviews()

        #Descargar imágenes...
        elif(self.STEP==3):
            self.downloadImages()

        print("Exiting " + self.name)

    #-------------------------------------------------------------------------------------------------------------------

    def getParams(self):

        url = "https://www.tripadvisor.com/RestaurantSearch&geo=" + str(self.GEO_ID)
        params = { 'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.111 Safari/537.36', }

        r = requests.get(url, headers=params)

        cookieDict = r.cookies.get_dict()
        cookieDict["TASession"] =cookieDict["TASession"].replace("TRA.true","TRA.false")

        cookieDict={"TAUnique":"%1%enc%3AP4eDoHhGTx3dk0g9tT58cSIjdxMtLaGxvCpuHkLALKBcZDjTQsqGzA%3D%3D",
                    "TASession":cookieDict["TASession"]}

        params["Cookie"] = ";".join(['%s=%s' % (name, value) for (name, value) in cookieDict.items()])
        params['cache-control'] = 'no-cache,no-store,must-revalidate'
        params["X-Requested-With"] = "XMLHttpRequest"

        return(params)

    def downloadRestaurants(self):

        def getPage(page):

            items_page = 30
            
            url = "https://www.tripadvisor.com/RestaurantSearch?Action=PAGE&geo=" + str(self.GEO_ID) + "&sortOrder=alphabetical&o=a" + str((page) * items_page)+"&ajax=1"

            s = requests.Session()
            s.cookies.set_policy(BlockAll())
            r = s.get(url,headers=self.PARAMS)

            return PyQuery(r.text),r

        #---------------------------------------------------------------------------------------------------------------

        data = []

        fromPage= self.DATA[0]
        toPage = self.DATA[1]

        for p in range(fromPage,toPage):
            print("Thread "+str(self.threadID)+": "+str(p+1)+" de "+str(toPage)+ "("+str(len(data))+")")

            pq,r = getPage(p)
            rst_in_pg = pq("div[data-test-target='restaurants-list']")

            rsts = rst_in_pg("div[data-test$='_list_item']").not_("div[data-test^='SL']")

            while(len(rsts)==0):
                print("Thread "+str(self.threadID)+" Error: Retrying connection...")
                time.sleep(5)

                pq, r = getPage(p)
                rst_in_pg = pq("div#EATERY_SEARCH_RESULTS")
                rsts = rst_in_pg("div.restaurants-list-ListCell__cellContainer--2mpJS")

            itms_pg = 0

            for r in rsts.items():

                # if len(r('div.ui_merchandising_pill')) > 0: continue

                name = r.find("a._15_ydu6b").text()
                name = re.sub(r"\d+\.\s", "", name)
                url = self.BASE_URL+r.find("a._15_ydu6b").attr("href")
                id_r = int(re.findall(r"d(\d+)", url)[0])
                rating = r.find("svg[title$='bubbles']")
                
                if len(rating)>0: rating = int(rating.attr("title").split(" of ")[0].replace(".", ""))
                else: rating=0

                t_a_p =r("div.MIajtJFg._1cBs8huC._3d9EnJpt span._1p0FLy4t")

                type_r = []; price = ""
                if len(t_a_p)==2:
                    type_r = t_a_p[0].text.split(", ")
                    price = t_a_p[1].text
                elif len(t_a_p)==1:
                    if("$" in t_a_p[0].text):
                        price = t_a_p[0].text
                    else:
                        type_r = t_a_p[0].text.split(", ")

                data.append((id_r, name, self.CITY, price, url, rating, type_r))

                itms_pg+=1

            if(itms_pg!=30):
                print("-"*100)
                print("Thread "+str(self.threadID)+": "+str(itms_pg)+" items in page " + str(p))
                print("-"*100)


        data = pd.DataFrame(data, columns=self.rest_cols)

        pd.to_pickle(data, self.TMP_FOLDER + "/restaurants-" + str(self.threadID) + ".pkl")

    #-------------------------------------------------------------------------------------------------------------------

    def completeReviews(self):

        def xpanReviews(RV):

            revs = []
            usrs = []

            ids = RV.reviewId.values
            rev_str = ','.join([str(x) for x in ids])

            data = {'reviews': rev_str, 'widgetChoice': 'EXPANDED_HOTEL_REVIEW_HSX', 'Action': 'install'}
            params = {'Content-Type': 'application/x-www-form-urlencoded'}
            r = requests.post("https://www.tripadvisor.com/OverlayWidgetAjax?Mode=EXPANDED_HOTEL_REVIEWS&metaReferer=Restaurant_Review",data=data, headers=params)

            pq = PyQuery(r.text)
            itms = pq.items("div[data-reviewlistingid]")


            for i in itms:
                revID = int(i.attr('data-reviewlistingid'))

                userData = i("div.avatar").attr("class").split(" ")
                if(len(userData)>1):
                    userID = i("div.avatar").attr("class").split(" ")[1].replace("profile_","")
                    userName = i("div.member_info .username").text()
                    userLocation = i("div.member_info .location").text()
                    usrs.append([userID, userName, userLocation])
                else:
                    userID = None

                rstID = RV.loc[RV.reviewId==revID].restaurantId.values[0]
                url = self.BASE_URL+i(".quote a").attr("href")

                title = i.find('a#rn' + str(revID) + ">span").text()
                text = i.find('p.partial_entry').text()

                date = i("span.ratingDate").attr("title")
                rating = int(i("span.ui_bubble_rating").remove_class("ui_bubble_rating").attr("class").replace("bubble_", ""))

                images = i.find("div.inlinePhotosWrapper")

                if(len(images)>0):
                    images = self.getImages(i)
                else:
                    images = []

                revs.append([revID,userID,rstID,title,text,date,rating,self.LANG,images,url])


            return revs,usrs

        #---------------------------------------------------------

        revs = []
        usrs = []

        RV = self.DATA

        total = len(RV)
        per_post = 100
        its = total // per_post

        allD = 0

        for i in range(its):
            print("Thread "+str(self.threadID)+": "+str(i+1)+" de "+str(its))

            data_from = i * per_post
            data_to = (i + 1) * per_post
            if(i==its-1): data_to = total

            temp_data = RV.iloc[data_from:data_to,:]
            t_revs,t_usrs = xpanReviews(temp_data)

            revs.extend(t_revs)
            usrs.extend(t_usrs)

        revs = pd.DataFrame(revs)
        revs.columns = self.review_cols

        usrs = pd.DataFrame(usrs)
        usrs.columns = self.user_cols

        pd.to_pickle(revs, self.TMP_FOLDER + "/reviews-" + str(self.threadID) + ".pkl")
        pd.to_pickle(usrs, self.TMP_FOLDER + "/users-" + str(self.threadID) + ".pkl")

    #-------------------------------------------------------------------------------------------------------------------

    def downloadImages(self):

        def saveImage(path, img_src):

            # si está descargada, skip
            if (os.path.isfile(path)): return True

            # gcontext = ssl.SSLContext(ssl.PROTOCOL_TLSv1)  # Only for gangstars

            try:
                a = urllib.request.urlopen(img_src)
            except:
                return False

            if (a.getcode() != self.SUCCESS_TAG):
                return False

            try:
                f = open(path, 'wb')
                f.write(a.read())
                f.close()
                return path
            except Exception as e:
                print(e)
                return False

        def download(revId, rev_url, images, highRes=False):

            ret = images

            if(highRes):path = self.PATH+"images/" + str(revId)
            else:path = self.PATH+"images_lowres/" + str(revId)

            os.makedirs(path, exist_ok=True)

            for item, i in enumerate(ret):
                name = path + "/" + str(item) + ".jpg"
                url_high_res = i['image_url_lowres']

                #Si ya se descargó y ocupa más de 0 saltar
                if os.path.exists(name):

                    if os.stat(name).st_size!=0 :

                        if(filetype.guess(name).mime!="image/jpeg"):
                            th_img = Image.open(name).convert('RGB')
                            th_img.save(name)
                        else:
                            continue

                    else: os.remove(name)

                # Cambiar la URL de la imagen low-res a la high-res

                if(highRes):
                    url_high_res = url_high_res.replace("/photo-l/", "/photo-o/")
                    url_high_res = url_high_res.replace("/photo-f/", "/photo-o/")

                    saved = saveImage(name, url_high_res)
                    if (not saved):
                        # Algunas veces hay que cambiarlo por photo-w
                        url_high_res = url_high_res.replace("/photo-o/", "/photo-w/")
                        saved = saveImage(name, url_high_res)
                        if (not saved):
                            # Algunas veces hay que cambiarlo por photo-p
                            url_high_res = url_high_res.replace("/photo-w/", "/photo-p/")
                            saved = saveImage(name, url_high_res)
                            if (not saved):
                                # Algunas veces hay que cambiarlo por photo-s
                                url_high_res = url_high_res.replace("/photo-p/", "/photo-s/")
                                saved = saveImage(name, url_high_res)
                                if (not saved): print("\nImg not saved: " + str(url_high_res) + " " + str(rev_url))

                else:
                    saved = saveImage(name, url_high_res)
                    if (not saved):
                        print("Error-"+str(url_high_res)+"-"+name)

                i['image_path'] = name
                i['image_high_res'] = url_high_res

            return ret
            # ------------------------------------------------------------

        RV = self.DATA

        # Para cada una de las reviews...
        for i, r in RV.iterrows():
            imgs = r.images
            revId = r.reviewId

            # Si tiene imagenes...
            if (len(imgs) > 0):
                print("Thread " + str(self.threadID) + ": " + str(i + 1) + " de " + str(len(RV)))

                r.images = download(revId, r.url, imgs,highRes=True)

    #-------------------------------------------------------------------------------------------------------------------

    def downloadReviewData(self):

        restaurants = self.DATA

        revs = []

        for i, r in restaurants.iterrows():

            print("Thread "+str(self.threadID)+": "+str(i+1)+" de "+str(len(restaurants)))
            rest_data = r
            rest_id = r.id

            #Si no hay reviews se salta
            try:res_hmtl = PyQuery(self.getHtml(r.url))
            except:
                print("NO_REVS",r.url)
                continue

            #Si no hay reviews se salta
            pg_revs = res_hmtl.find("div.reviewSelector")
            if(len(pg_revs)==0):
                print("NO_REVS",r.url)
                continue

            #Obtener el número de revs
            total_num = res_hmtl.find("label[for='filters_detail_language_filterLang_"+self.LANG+"']>span.count")[0].text.replace("(","").replace(")","").replace(",","")
            total_num = int(total_num)

            rv = self.getReviews(res_hmtl, rest_id, rest_data,total_num)

            if(len(rv)!=total_num):
                print("ERROR",r.url)
                print("%d de %d" % (len(rv),total_num))

            revs.extend(list(zip(rv,[r.id]*len(rv))))


        print("Saving...")

        revs = pd.DataFrame(revs)
        revs.columns = ["reviewId","restaurantId"]

        pd.to_pickle(revs, self.TMP_FOLDER + "/reviews-"+str(self.threadID)+".pkl")

    def getReviews(self, pq, rest_id, rest_data,total_num):

        ids = []

        # Si existe el boton, hay más páginas
        if (total_num>10):

            i = 1

            temp_url = rest_data['url']

            pages = total_num//10
            if(total_num%10>0):pages+=1

            for p in range(pages):

                #usr_data, rev_data, cont = self.parseReviewPage(pq, temp_url, rest_id, rest_data)

                tmp_ids = list(map(lambda x: int(x.attr("data-reviewid")),pq.items("div.reviewSelector")))
                ids.extend(tmp_ids)

                #revs = revs.append(rev_data)
                #usrs = usrs.append(usr_data)

                #Si se cortó en medio de la página, son traducciones
                #if (len(revs)<10): break
                if (len(tmp_ids)<10): break

                temp_url = rest_data['url'].replace("-Reviews-", "-Reviews-or" + str(i * 10) + "-")
                i += 1

                try:
                    pq = PyQuery(self.getHtml(temp_url))
                except:
                    print(url)

        else:

            #usrs, revs, cont = self.parseReviewPage(pq, rest_data['url'], rest_id, rest_data)
            ids = list(map(lambda x: int(x.attr("data-reviewid")), pq.items("div.reviewSelector")))

        return ids

    def parseReviewPage(self,pq, page_url, rest_id, rest_data):

        rev_data = pd.DataFrame(columns=self.review_cols)
        usr_data = pd.DataFrame(columns=self.user_cols)

        for rev in pq.items("div.review-container"):

            # Si aparece el banner, no continuar, las demás son traducidas
            if (rev("div.translationOptions")):
                return usr_data, rev_data, 0

            rev_id = int(rev("div.reviewSelector").attr("data-reviewid"))
            rev_title = rev("span.noQuotes").text()
            rev_url = self.BASE_URL + str(rev("div.quote>a").attr("href"))
            rev_date = rev("span.ratingDate").attr("title")
            rev_rating = int(rev("span.ui_bubble_rating").remove_class("ui_bubble_rating").attr("class").replace("bubble_", ""))
            rev_content = None
            rev_images = []

            user_id = str(rev("div.avatar").remove_class("avatar").attr("class"))[8:]

            user_name = rev("div.info_text div")[0].text
            user_loc = rev("div.info_text div strong").text()

            # Ver si se puede expandir
            more = rev("div.prw_rup.prw_reviews_text_summary_hsx>div.entry>p.partial_entry>span.taLnk.ulBlueLinks")

            # Si no se puede expandir, obtener el texto
            if (not more):
                rev_content = rev("div.prw_rup.prw_reviews_text_summary_hsx>div.entry>p.partial_entry").text()

            # Si hay imagenes, obtener los links
            images = rev("div.inlinePhotosWrapper")

            if (images):
                rev_images = self.getImages(rev)

            # addUser(userId=user_id,username=user_name,location=user_loc)
            # addReview(reviewId=rev_id,userId=user_id,restaurantId=rest_id,title=rev_title, text=rev_content,date=rev_date,rating=rev_rating,url=rev_url,language="es",images=rev_images)

            rev_content = {'reviewId': rev_id, 'userId': str(user_id), 'restaurantId': str(rest_id), 'title': rev_title,
                           'text': rev_content, 'date': rev_date, 'rating': rev_rating, 'language': "es",
                           'images': rev_images, 'url': rev_url}
            rev_data = rev_data.append(rev_content, ignore_index=True)

            usr_content = {'id': user_id, 'name': user_name, 'location': user_loc}
            usr_data = usr_data.append(usr_content, ignore_index=True)

        return usr_data, rev_data, 1

    def getImages(self,dt):

            ret = []

            for img in dt.items("noscript>img.centeredImg.noscript"):
                ret.append({"image_url_lowres": img.attr("src"), "image_path": "", "image_high_res": ""})
            return ret

    def appendPickle(self,itm, name):

        if os.path.isfile(name):
            file = pd.read_pickle(name)
            file = file.append(itm, ignore_index=True)
            pd.to_pickle(file, name)
        else:
            pd.to_pickle(itm, name)

    def getHtml(self,url):

        data = {'filterLang': self.LANG,
                "changeSet": "REVIEW_LIST"
                }

        #Reintentar la petición mientras no se obtenga resultado

        r = ''
        while r == '':
            try:
                r = requests.post(url, data=data, headers=self.PARAMS)
                break
            except:
                time.sleep(5)
                continue


        html = r.text

        r.close()

        return html

