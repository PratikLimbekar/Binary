from intent_classifier import classify_intent
from gemini import getairesponse
from note_manager import save_note
from wikipedia_search import search_wikipedia
from weather import getweather
from news import getnews
from genimg import genimg
import os
import psutil
import mediacontrols

def route_command(userinput: str):
    """
    Routes user input to actions based on intent classification
    Returns: 
    str: the response text or action result."""

    intent = classify_intent(userinput)
    # if intent =='ask_question' or 'introductions': #this is always true lmao
    if intent in ['ask_question', 'introductions', 'fallback']: #correct
        return getairesponse(userinput)
    if intent =='open_app':
        return open_app(userinput)
    if intent == 'get_system_info':
        return getsysinfo()
    if intent == 'create_note':
        return save_note(userinput)
    if intent == 'wikipedia_search':
        return search_wikipedia(userinput)
    if intent == 'music_controls':
        return musiccontrol(userinput)
    if intent == 'get_weather':
        return getweather()
    if intent == 'get_news':
        return getnews()
    if intent == 'generate_image':
        return genimg(userinput)
    else:
        return intent
    

def getsysinfo()->str:
    battery = psutil.sensors_battery()
    cpu = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')

    response_parts = []

    if battery:
        response_parts.append(f"Battery at {battery.percent}%")
    response_parts.append(f"CPU usage is {cpu}%")
    response_parts.append(f"RAM usage is {memory.percent}%")
    response_parts.append(f"Disk usage is {disk.percent}%")
    print("getting system information.")
    return "\n".join(response_parts)

def musiccontrol(userinput):
    userinput = userinput.lower()

    if any(word in userinput for word in ["pause", "stop", "halt"]):
        return mediacontrols.pausemusic()
    elif any(word in userinput for word in ["resume", "continue", "play"]):
        return mediacontrols.pausemusic()
    elif any(word in userinput for word in ["next", "skip", "forward"]):
        return mediacontrols.nexttrack()
    elif any(word in userinput for word in ["previous", "back", "rewind", "last"]):
        return mediacontrols.prevtrack()
    else:
        return "unknown"


def open_app(appname: str) -> str:#expected to return string
    """
    opens app 
    """
    app_commands = {
        "browser": "start chrome",
        "chrome": "start chrome",
        "edge": "start edge",
        "open edge": "start msedge",
        "vscode": "code",
        "notepad": "notepad",
        "explorer": "explorer",
        "desktop" : r"C:\Users\iprat\OneDrive\Desktop" ,
        "notion":'start "" "C:\\Users\\iprat\\AppData\\Roaming\\Microsoft\\Windows\\Start Menu\\Programs\\Notion"'
    }

    for key in app_commands:
        if key in appname.lower():
            os.system(app_commands[key])
            return f'Opening {key}'
    return "Sorry, I don't know that app."