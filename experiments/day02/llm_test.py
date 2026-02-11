
from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()

client = OpenAI()

response = client.chat.completions.create(

    model="gpt-4o-mini",
    messages=[
        {"role":"system","content":"You are a concise assistant."},
        {"role":"user","content":"Explain in 2 lines what an AI agent is."}
    ]
)

print(response.choices[0].message.content)