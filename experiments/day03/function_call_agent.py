
from openai import OpenAI
from dotenv import load_dotenv
import os
import datetime
import json

load_dotenv()
client = OpenAI()

#---------TOOL----------

def get_current_time():
    return datetime.datetime.now().strftime("%H:%M:%S")


#---- Define Tool Schema for the LLM -----

tools = [
    {
        "type":"function",
        "function": {
           "name": "get_current_time",
            "description":"Returns the current system time",
            "parameters":{
                "type":"object",
                "properties": {},
                "required": []
            }
        }
    }
]

#------ Tool Registry ---------

tool_registry = {
    "get_current_time":get_current_time
}

# ---- user input ------

user_question = " what is the time right now?"

# ----- First LLM call ------

reponse = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "user","content":user_question}
    ],
    tools=tools
)

message = reponse.choices[0].message

if message.tool_calls:
    tool_call = message.tool_calls[0]

    function_name = tool_call.function.name
    arguments = json.loads(tool_call.function.arguments)

    print ("Model  requested tool ",function_name)

    # Execute Dynamically
    tool_result = tool_registry[function_name](**arguments)

    second_response = client.chat.completions.create(

        model="gpt-4o-mini",
        messages=[{"role":"user","content": user_question},
                  message,
                  {
                      "role":"tool",
                       "tool_call_id": tool_call.id, 
                        "content":tool_result
                  }
                  ]
    )

    print("Final Answer:", second_response.choices[0].message.content)
else:
   print("Direct Answer:", message.content)