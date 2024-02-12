import json
import requests
import openai
from tenacity import retry, wait_random_exponential, stop_after_attempt
from openai import OpenAI

GPT_3 = "gpt-3.5-turbo"
GPT_4 = "gpt-4-turbo-preview"

with open('api_key.txt','r') as f:
  openai.api_key = f.read()
api_key = openai.api_key

client = OpenAI(api_key=api_key)

@retry(wait=wait_random_exponential(multiplier=1, max=40), stop=stop_after_attempt(3))
def chat_completion_request(messages, tools=None, tool_choice=None, model=GPT_3):
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + openai.api_key,
    }
    json_data = {"model": model, "messages": messages}
    if tools is not None:
        json_data.update({"tools": tools})
    if tool_choice is not None:
        json_data.update({"tool_choice": tool_choice})
    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=json_data,
        )
        return response
    except Exception as e:
        print("Unable to generate ChatCompletion response")
        print(f"Exception: {e}")
        return e
    
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_current_weather",
            "description": "Get the current weather",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city and state, e.g. San Francisco, CA",
                    },
                    "format": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                        "description": "The temperature unit to use. Infer this from the users location.",
                    },
                },
                "required": ["location", "format"],
            },
        }
    }
]

def get_location(message, messages):
    messages.append({"role": "system", "content": "Don't make assumptions about what values to plug into functions. Ask for clarification if a user request is ambiguous."})
    messages.append({"role": "user", "content": message.content})
    chat_response = chat_completion_request(
        messages, tools=tools, tool_choice = 'auto'
    )
    return chat_response.json()["choices"][0]["message"]

def get_weather(location):
    url = "http://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": location,
        "APPID": "3128f76a7551a274746e884fd29a0e8f"
    }
    return requests.get(url, params=params) #  'temp' : response.json()['main']['temp']

def write_description(data, loc, unit, messages):
    info = {'location' : loc, 'temp' : data.json()['main']['temp'], 'unit' : unit}
    messages.append({"role": "system", "content": "Provide a short description about the weather. Adjust the temperature unit from Kelvin to given unit, e.g The temperature in Yerevan is -1.91 degrees Celsius"})
    messages.append({"role": "user", "content": f'{loc} , {data.json()['main']['temp']} Kelvin, {unit}'})
    chat_response = chat_completion_request(
        messages, tools=None, tool_choice = None
    )
    assistant_message = chat_response.json()["choices"][0]["message"]
    messages.append(assistant_message)
    return assistant_message['content']

def translate(messages):
    messages.append({"role": "user", "content": "translate the your last response to armenian."}) #changed to gpt 4, as gpt3 couldn't handle this task
    chat_response = chat_completion_request(
        messages, tools=None, tool_choice = None, model = GPT_4
    )
    assistant_message = chat_response.json()["choices"][0]["message"]
    messages.append(assistant_message)
    return (weather_arm := assistant_message['content'])

def num_to_word(messages):
    messages.append({"role": "user", "content": "change the numbers of your last message to words. e.g. Երևանում ջերմաստիճանը մինուս մեկ ու կես ցելսիուս է։"}) #T2V can't generate armenian numbers from numbers in text
    chat_response = chat_completion_request(
        messages, tools=None, tool_choice = None,  model = GPT_4
    )
    assistant_message = chat_response.json()["choices"][0]["message"]["content"]
    messages.append({"role": "system", "content": assistant_message})
    
def get_voice(messages):
    response = client.audio.speech.create(
    model="tts-1-hd",
    voice="alloy",
    input=messages[-1]['content']
    )
    response.stream_to_file("եղանակ.mp3")
    path = './եղանակ.mp3'
    return path
    
        
def get_image(messages):
    global client
    response = client.images.generate(
    model="dall-e-3",
    prompt= messages[2]['content'],
    size="1024x1024",
    quality="standard",
    n=1,
    )
    image_url = response.data[0].url
    img_data = requests.get(image_url).content
    with open('weather_image.jpg', 'wb') as handler:
        handler.write(img_data)
    image_path = './weather_image.jpg'
    return image_path, image_url
    
        
def get_text_image(image_url):
    response = client.chat.completions.create(
    model="gpt-4-vision-preview",
    messages=[
        {
        "role": "user",
        "content": [
            {"type": "text", "text": "Is there text in the image? If yes what is it? DONT DESCRIBE THE IMAGE. OUTPUT ONLY TEXT THAT THERE IS ON IT"},
            {
            "type": "image_url",
            "image_url": {
                "url": image_url,
            },
            },
        ],
        }
    ],
    max_tokens=300,
    )
    return response.choices[0].message.content
