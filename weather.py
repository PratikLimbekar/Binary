import requests
from dotenv import load_dotenv
import os

load_dotenv()
apikey = os.getenv("weather_key")
baseurl = "https://api.openweathermap.org/data/2.5/weather"

def getweather(city: str = "Pune") -> str:
    try:
        params = {
            'q':city,
            'appid': apikey,
            'units':'metric'
        }
        response = requests.get(baseurl, params = params)
        data = response.json()

        if response.status_code != 200 or data.get('cod') != 200:
            return f"Sorry, couldn't get weather info."
        
        weather = data['weather'][0]['description']
        temp = data['main']['temp']
        feels_like = data['main']['feels_like']
        humidity = data['main']['humidity']

        return (
            f"Weather in {city}:\n"
            f"- Condition: {weather.capitalize()}\n"
            f"- Temperature: {temp}°C (Feels like {feels_like}°C)\n"
            f"- Humidity: {humidity}%"
        )
    
    except Exception as e:
        return f"Error getting weather: {str(e)}"
