print("STEP 1: script started")

import os
from dotenv import load_dotenv
print("STEP 2: imports worked")

from langchain_google_genai import ChatGoogleGenerativeAI
print("STEP 3: langchain import worked")

load_dotenv()
key = os.getenv("GOOGLE_API_KEY")
print("STEP 4: key loaded?", "YES, length=" + str(len(key)) if key else "NO — key is missing/empty")

llm = ChatGoogleGenerativeAI(
    model="gemini-3.5-flash-lite",
    api_key=key
)
print("STEP 5: model object created")

response = llm.invoke("Say hello in one short sentence.")
print("STEP 6: got response")
print("RESPONSE:", response.content)