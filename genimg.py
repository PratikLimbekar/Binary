from dotenv import load_dotenv
import os
from PIL import Image
from google.genai import types
from io import BytesIO
from google import genai
import os

load_dotenv()
apikey= os.getenv('gemini_api_key')
client = genai.Client(api_key=apikey)

def genimg(input):
    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash-preview-image-generation', contents = input,
            config=types.GenerateContentConfig(
                response_modalities=['TEXT', 'IMAGE']
            )
        )
        
        for part in response.candidates[0].content.parts:
            if part.inline_data is not None:
                image = Image.open(BytesIO((part.inline_data.data)))
                image.save("1.png")
                print("obtained image")
                image.show()
            elif part.text is not None:
                print(part.text)
    except Exception as e:
        print("Exception")
        return None
    return part.text