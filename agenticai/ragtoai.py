from google import genai
from dotenv import load_dotenv
import os

#gemini
load_dotenv()
apikey = os.getenv('gemini_api_key')
client = genai.Client(api_key=apikey)


#following function sends text to AI
def ragbasedresponse(query, context_chunks):
    context = "\n\n".join(context_chunks)
    prompt = f"""Use the context below to answer the question. If the answer isn't in the context, say "Not found."

    Context:
{context}

Question: {query}
Answer:"""
    
    try:
        response = client.models.generate_content(
        model="gemini-2.0-flash", contents = prompt
        )
        print(response.text)
        return response.text
    except Exception as e:
        return "Sorry, cannot comprehend this. Me just a pet bro."
