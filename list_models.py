import os
from dotenv import load_dotenv
from google import genai

load_dotenv()
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

for m in client.models.list():
    # only show models that can do generateContent (what we need)
    if "generateContent" in getattr(m, "supported_actions", []) or True:
        print(m.name)