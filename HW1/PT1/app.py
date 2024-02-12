#import required dependencies
import json
import requests
import openai
from tenacity import retry, wait_random_exponential, stop_after_attempt
from openai import OpenAI
import chainlit as cl
import os
import functions as fc

messages = []

@cl.on_chat_start
async def chat_start():
    await cl.Message(
        content="Hi! I am your weather chat app. Ask me about the weather and see what I can do!",
    ).send()




@cl.on_message
async def main(message: cl.Message):
    global messages
    msg = cl.Message(content="")
    await msg.send()
    global messages  
    # START THE CONVERSATION
    assistant_message = fc.get_location(message,messages)
    
    if assistant_message['content']:# GET CLARIFICATION IF NEEDED
        msg.content = assistant_message['content']
        await msg.update()
        messages.append(assistant_message)
        main(cl.Message)
        
    else: # RETRIEVE WEATHER LOCATION AND TEMPERATURE UNIT
        loc = assistant_message['tool_calls'][0]['function']['arguments'].split('"')[3]
        unit = assistant_message['tool_calls'][0]['function']['arguments'].split('"')[7]
        
        # CALL WEATHER API TO GET WEATHER DATA
        weather_data = fc.get_weather(loc)
        
        # CALL API TO WRITE SHORT WEATHER DESCRIPTION
        weather_english = fc.write_description(weather_data, loc, unit,messages)

        # CALL API TO TRANSLATE TO ARMENIAN
        weather_arm = fc.translate(messages)
        
        # CALL API TO CHANGE NUMBERS TO WORDS
        fc.num_to_word(messages)
        
        # CALL API FOR V2T 
        audio_path = fc.get_voice(messages)
        
        # GENERATE IMAGE this part is written here istead of function because it cause openai security error when used as separate function
        image_path, image_url = fc.get_image(messages)

        # GET TEXT FROM THE IMAGE
        text_from_image = fc.get_text_image(image_url)
        
        elements = [
            cl.Text(name="Get the weather in given location", content=weather_english, display="inline"),
            cl.Text(name="Translate to Armenian", content=weather_arm, display='inline'),
            cl.Audio(name="The audio of weather in armenian", path = audio_path, display="inline"),
            cl.Image(name= "Visualization of weather", path = image_path, display="inline"),
            cl.Text(name="Text in image", content = text_from_image, display='inline')]
        

        msg.content = "Here is the result"
        msg.elements = elements
        await msg.update()