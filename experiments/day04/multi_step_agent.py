
from openai import OpenAI
from dotenv import load_dotenv
import os
import datetime
import json

load_dotenv()
client = OpenAI()

#-------tool Defination------------

def get_current_time():
    return datetime.datetime.now().strftime("%H:%M:%S")


#-------tool Schema (LLM View) ------------

tools = [
    {
        "type":"function",
        "function":{
            "name": "get_current_time",    
            "description":"Returns the current system time in HH:MM:SS format.",
            "parameters":{
                "type":"object",
                "properties":{},
                "required": []    
            }
        }
    }
 ]

#-------tool Registry------------

tool_registry = {"get_current_time": get_current_time}



#-------User Input------------

user_question = "Tell me the current time and confirm it again"


#-------Conversation Memory------

conversation = [{"role":"user","content": user_question}]

max_step =5
step =0

#-------Agent Loop------------

while step < max_step:
    step += 1
    print(f"\n--- step {step} ---")

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=conversation,
        tools=tools
    )

    message = response.choices[0].message
    conversation.append(message)

    if message.tool_calls:
        for tool_call in message.tool_calls:
            function_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)

            print("Model requested tool:", function_name)

            if function_name in tool_registry:
                tool_result = tool_registry[function_name](**arguments)
            else:
                tool_result = f"ERROR: Tool '{function_name}' not available."
    
            print("Tool Result:", tool_result)

            conversation.append({
                "role":"tool",
                "tool_call_id":tool_call.id,
                "content": tool_result
            })
    else:
        print("\nFinal Answer:", message.content)
        break

