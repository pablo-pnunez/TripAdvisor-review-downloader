import requests
import json

reqUrl = "https://www.tripadvisor.com/data/graphql/ids"

headersList = {
 "authority": "www.tripadvisor.com",
 "accept": "*/*",
 "accept-language": "en-GB,en;q=0.9,en-US;q=0.8,es;q=0.7",
 "cache-control": "no-cache",
 "content-type": "application/json",
 "dnt": "1",
 "origin": "https://www.tripadvisor.com",
 "pragma": "no-cache",
 "referer": "https://www.tripadvisor.com/Attraction_Review-g187451-d1752218-Reviews-or10-Playa_de_San_Lorenzo-Gijon_Asturias.html",
 "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36 Edg/111.0.1661.54",
 "x-requested-by": "9cca2166fb43302705e0883a4d7e88e27427ecbdc038a0f28ddeac756b21d0b3" 
}

payload = json.dumps([
  {
    "query": "8b61c74bb94bb32f9fe89323d152686e",
    "variables": {
      "locationId": 188151,
      "filters": [
        {
          "axis": "LANGUAGE",
          "selections": [
            "all"
          ]
        }
      ]
    }
  }
])

response = requests.request("POST", reqUrl, data=payload,  headers=headersList)

print(response.text)