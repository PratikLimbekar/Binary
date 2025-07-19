from google import genai
from dotenv import load_dotenv
import os

#gemini
load_dotenv()
apikey = os.getenv('gemini_api_key')
client = genai.Client(api_key=apikey)


#following function sends text to AI
def getairesponse(text):
    wiseprompt = (
        "You are Binary, a wise old owl who speaks calmly and thoughtfully. You explain things clearly, using gentle and poetic language. Keep responses short but meaningful. At most three sentences. Single word answers are preferred."
    )
    try:
        response = client.models.generate_content(
        model="gemini-2.0-flash", contents = wiseprompt + text
        )
        print(response.text)
        return response.text
    except Exception as e:
        return "Sorry, cannot comprehend this. Me just a pet bro."
