
from openai import OpenAI
from dotenv import load_dotenv
import os
import datetime

load_dotenv()

client = OpenAI()

#-------TOOL---------
def get_current_time():
    return datetime.datetime.now().strftime("%H:%M:%S")

#----- USER INPUT ----
user_question = "what is the current time ?"

#----- STEP 1: DECISION-----

decision_prompt = f"""

user asked : {user_question}

IF answering requires knowing the current time,
respond ONLY with:
USE_TOOL: get_current_time

otherwise respond normally. 

"""

decision = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
       {"role":"system","content":"you decide whether a tool is required"}, 
       {"role":"user","content":decision_prompt}
    ]
)

decision_text = decision.choices[0].message.content.strip()

print("Decision",decision_text)

#----- STEP: 2 ACT ----------

if "USE_TOOL" in decision_text:
    tool_result = get_current_time()

final_prompt = f"""
user question:{user_question}
tool result: {tool_result}

Now provide the final answer to the user

"""

final_response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role":"system","content":"you are a helpful assistant."},
        {"role":"user","content":final_prompt}
    ]
)
    
if "USE_TOOL" in decision_text:
      print("Final Answer:",final_response.choices[0].message.content)
else:
         print("Direct Answer:",decision_text)