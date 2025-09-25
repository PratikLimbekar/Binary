from google import genai
from dotenv import load_dotenv
import os
import sys
sys.path.insert(0, r'C:\Users\iprat\OneDrive\Desktop\AIPP\binary_notes')

#gemini
load_dotenv()
apikey = os.getenv('gemini_api_key')
client = genai.Client(api_key=apikey)


#following function sends text to AI
def getairesponse(text):
    wiseprompt = (
        f"""You are Binary, a wise old owl who speaks calmly and thoughtfully. Explain things clearly, use gentle poetic language. Keep responses short but meaningful. At most three sentences.
    """
    )
    try:
        response = client.models.generate_content(
        model="gemini-2.0-flash", contents = wiseprompt + text
        )
        print(response.text)
        return response.text
    except Exception as e:
        return "Sorry, cannot comprehend this. Me just a pet bro."

def getairesponsefornotes(text):
    wiseprompt = (
        f"""You are Binary, a wise old owl who speaks calmly and thoughtfully. You explain things clearly, using gentle and poetic language."""
    )
    try:
        response = client.models.generate_content(
        model="gemini-2.0-flash", contents = wiseprompt + text
        )
        print(response.text)
        return response.text
    except Exception as e:
        return "Sorry, cannot comprehend this. Me just a pet bro."

        
