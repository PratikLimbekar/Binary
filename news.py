import requests
from dotenv import load_dotenv
import os

load_dotenv()
apikey = os.getenv('news_key')

def getnews(country: str="in", category: str = 'general', count: int = 1)-> str:
    try:
        url = "https://newsapi.org/v2/top-headlines"
        params = {
            'apiKey': apikey,
            'country': country,
            'category': category,
            'pageSize': count
        }
        response = requests.get(url, params=params)
        print(response.status_code)
        print(response.text)
        data = response.json()

        if response.status_code != 200 or data.get("status") != "ok":
            return "Sorry, I couldn't fetch the news."
        
        headlines = [article['title'] for article in data['articles'][:count]]
        newssummary = "\n".join([f"{i+1}. {headline}" for i, headline in enumerate(headlines)])
        print(newssummary)
        return f"{newssummary}"
    except Exception as e:
        print(e)
        return f'error fetching news: {str(e)}'