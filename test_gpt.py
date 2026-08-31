import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

llm = ChatOpenAI(
    model="gpt-4.1-mini",
    api_key=os.getenv("AZURE_OPENAI_KEY"),
    base_url=os.getenv("AZURE_OPENAI_ENDPOINT"),
)

response = llm.invoke("Say hello in one short sentence.")
print("RESPONSE:", response.content)