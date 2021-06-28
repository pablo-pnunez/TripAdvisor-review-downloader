from pyquery import PyQuery as pq
from tqdm import tqdm
import pandas as pd
import numpy as np
import re

regex = r"\"coords\":\"(-?\d+\.\d+),(-?\d+\.\d+)\""
path = "/media/nas/pperez/data/TripAdvisor/malaga_data/"

# rsts = pd.read_pickle(path+"restaurants_new.pkl")
# print(rsts[["gps", "tags"]])

# exit()

rsts = pd.read_pickle(path + "restaurants.pkl")

coords = []
tags = []

for _, rs in tqdm(rsts.iterrows(), total=len(rsts)):
    try:
        content = pq(url = rs["url"], headers={"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36",
                                            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9"})

    except:
        print(rs["url"])

    data = content("script:contains('\"coords\":\"')")[0].text
    data = re.findall(regex, data)

    coords.append(data[0])
    
    tags_list = content("div._1XLfiSsv")
    rst_tags = []
    
    if len(tags_list)>0:
        tags_title_list = np.asarray(list(map(lambda x: x.text,content("div._14zKtJkz"))))
        if "Tipos de cocina" in tags_title_list:
            coc_pos = np.where(tags_title_list == 'Tipos de cocina')[0][0]
            rst_tags = content("div._1XLfiSsv")[coc_pos].text.split(", ")

    tags.append(rst_tags)

    print("\n",rs["name"], coords[-1], tags[-1])


rsts["gps"] = coords
rsts["tags"] = tags

rsts.to_pickle(path+"restaurants_new.pkl")
