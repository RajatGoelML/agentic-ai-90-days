
from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()
client = OpenAI()

def asl_llm(system_prompt: str, user_prompt: str) -> str:

    response = client.chat.completions.create(

            model="gpt-4.1-mini",
            messages=[
                {"role":"system", "content":system_prompt},
                {"role":"user", "content":user_prompt}
            ],
            temperature=0
    )

    content = response.choices[0].message.content.strip()

    return {
        "prompt": user_prompt,
        "response": content
    }
    