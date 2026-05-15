import os
import re
import psutil
from src.modules.note_manager import save_note
from src.modules.wiki_module import search_wikipedia
from src.modules.weather_module import getweather
from src.modules.news_module import getnews
from src.modules import media_controls as mediacontrols
from src.services.timer_service import timer_service
from src.services.audio_service import audio_service
from src.services.finance_service import finance_service
from src.services.workspace_service import workspace_service
from src.services.app_launcher_service import app_launcher

import json
import re
from src.services.hybrid_llm_service import hybrid_llm as llm

def llm_decide(userinput: str):
    # Routing doesn't need context, disabling history saves time/RAM
    response = llm.chat(userinput, include_history=False)
    response = response.strip()

    # Check if response looks like JSON (starts with { or [)
    if response.startswith('{') or response.startswith('['):
        try:
            data = json.loads(response)
            if isinstance(data, dict) and "type" in data:
                result = data
            else:
                result = {"type": "chat", "response": response}
        except:
            # JSON parsing failed, treat as plain text chat
            result = {"type": "chat", "response": response}
    else:
        # Plain text response - it's a chat answer
        result = {"type": "chat", "response": response}
    
    # Clear history after each response to minimize memory usage
    llm.clear_history()
    return result

VALID_TOOLS = {
    "set_timer",
    "play_audio",
    "log_finance",
    "launch_workspace"
}

def execute_tool(action: str, params: dict):
    if action == "set_timer":
        try:
            # Be flexible: accept 'minutes', 'duration', or 'time'
            mins = int(params.get("minutes") or params.get("duration") or params.get("time") or 1)
        except:
            mins = 1
        timer_service.start_timer("Timer", mins)
        return f"I have started a {mins} minute timer for you."

    if action == "play_audio":
        return audio_service.play_ambient(str(params.get("track_name", "rain")))

    if action == "log_finance":
        try:
            amt = float(params.get("amount", 0))
        except:
            amt = 0.0
        return finance_service.log_transaction(
            amt,
            str(params.get("category", "misc")),
            str(params.get("description", "")),
            trans_type=str(params.get("trans_type", "Expense"))
        )

    if action == "launch_workspace":
        return workspace_service.launch_workspace(
            params.get("name", "default")
        )

    return "Unknown tool."

def handle_intent(intent: str, userinput: str):
    if intent in ['ask_question', 'introductions', 'fallback']:
        # Static chat is faster and avoids UI flooding
        return llm.chat(userinput, include_history=True)
    if intent =='open_app':
        # Try the smart launcher first, fall back to hardcoded list
        result = app_launcher.launch_app(userinput)
        if "Could not find" in result:
            return open_app(userinput)
        return result
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
    if intent == 'start_focus_mode':
        return handle_focus_intent(userinput)
    if intent == 'ambient_audio':
        return handle_audio_intent(userinput)
    if intent == 'workspace_launcher':
        return handle_workspace_intent(userinput)
    if intent == 'finance_log':
        return handle_finance_intent(userinput)
    else:
        return llm.chat(userinput, include_history=True)

def route_command(userinput: str):
    """
    Routes user input to actions based on intent classification
    Returns: 
    str: the response text or action result."""

    # --- FAST-PATH CACHE (Regex) ---
    cmd = userinput.lower().strip()
    
    # Quick app launch
    if cmd.startswith("open "):
        return handle_intent("open_app", userinput), "intent"
        
    # Quick ambient audio
    if cmd.startswith("play ") and any(x in cmd for x in ["rain", "storm", "cafe", "forest", "waves"]):
        sound = cmd.replace("play ", "").strip()
        return execute_tool("play_audio", {"track_name": sound}), "action"

    # Quick timer
    timer_match = re.search(r"set timer for (\d+) minutes?", cmd)
    if timer_match:
        return execute_tool("set_timer", {"minutes": int(timer_match.group(1))}), "action"
    
    # --- LLM BRAIN (Slow-Path) ---
    intent = llm_decide(userinput)

    t = intent.get("type")

    if t == "chat":
        return intent.get("response", "The forest is quiet, my thoughts are still gathering..."), "chat"

    if t == "tool_call":
        action = intent.get("action")
        params = intent.get("parameters", {})
        
        if action not in VALID_TOOLS:
            return f"The tool '{action}' is not in my repertoire yet.", "chat"

        return execute_tool(action, params), "action"
    
    if t == "intent":
        name = intent.get("name")
        return handle_intent(name, userinput), f"intent: {name}"
    
    return handle_intent("ask_question", userinput), "chat"
    

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

# Keyword maps for audio and categories
AUDIO_KEYWORDS = {
    "rain": "rain", "thunder": "storm", "storm": "storm",
    "cafe": "cafe", "coffee": "cafe", "forest": "forest",
    "ocean": "ocean", "waves": "ocean", "white noise": "white_noise",
    "brown noise": "brown_noise", "fire": "fireplace", "fireplace": "fireplace"
}
FINANCE_CATEGORIES = {
    "food": ["food", "lunch", "dinner", "breakfast", "eat", "restaurant", "coffee", "snack", "groceries"],
    "transport": ["uber", "ola", "auto", "cab", "petrol", "fuel", "metro", "bus", "train"],
    "shopping": ["amazon", "flipkart", "clothes", "shirt", "shoes", "online"],
    "entertainment": ["movie", "netflix", "spotify", "game", "concert"],
    "utilities": ["electricity", "internet", "wifi", "phone", "bill", "recharge"],
    "income": ["salary", "freelance", "income", "payment received", "got paid"]
}

POMODORO_PRESETS = {
    "deep work": 50, "pomodoro": 25, "short": 5, "long break": 15,
    "study sprint": 90, "sprint": 90, "classic": 25
}

def extract_minutes(text):
    """Extracts a duration in minutes from natural language."""
    text_lower = text.lower()
    for preset_name, minutes in POMODORO_PRESETS.items():
        if preset_name in text_lower:
            return minutes
    match = re.search(r'(\d+)\s*(min|minute|minutes|hour|hours|hr|hrs|sec|second|seconds)', text_lower)
    if match:
        val = int(match.group(1))
        unit = match.group(2)
        if "hour" in unit or "hr" in unit:
            return val * 60
        if "sec" in unit:
            return max(1, val // 60)
        return val
    return 25  # default

def extract_amount(text):
    """Extracts a numeric amount from text."""
    match = re.search(r'[₹rs\.\s]*(\d+[\.\d]*)', text.lower())
    return float(match.group(1)) if match else 0.0

def categorize_expense(text):
    """Returns (category, trans_type) from text keywords."""
    text_lower = text.lower()
    for cat, keywords in FINANCE_CATEGORIES.items():
        if any(kw in text_lower for kw in keywords):
            trans_type = "Income" if cat == "income" else "Expense"
            return cat.title(), trans_type
    return "Miscellaneous", "Expense"

def handle_focus_intent(userinput):
    """Handles focus/timer-related commands."""
    lower = userinput.lower()
    
    # Query remaining time
    if any(w in lower for w in ["how much", "time left", "remaining"]):
        active = timer_service.get_all_active()
        if active:
            t = active[0]
            mins = int(t['remaining'] // 60)
            secs = int(t['remaining'] % 60)
            return f"{t['name']} timer: {mins}m {secs}s remaining."
        return "No active timers running."
    
    # Pause / Resume
    if "pause" in lower:
        active = timer_service.get_all_active()
        if active:
            timer_service.pause_timer(active[0]['id'])
            return "Timer paused."
        return "No active timer to pause."

    if any(w in lower for w in ["resume", "continue"]):
        active = timer_service.get_all_active()
        if active:
            timer_service.resume_timer(active[0]['id'])
            return "Timer resumed."
        return "No active timer to resume."

    # Stop timer
    if any(w in lower for w in ["stop", "end", "cancel"]):
        active = timer_service.get_all_active()
        if active:
            tid = active[0]['id']
            with timer_service.lock:
                if tid in timer_service.active_timers:
                    del timer_service.active_timers[tid]
            return "Timer stopped."
        return "No active timers to stop."
    
    # Start / resume
    duration = extract_minutes(userinput)
    name = "Focus"
    if "break" in lower:
        name = "Break"
    timer_id = timer_service.start_timer(name, duration)
    return f"Started {name} timer for {duration} minutes."

def handle_audio_intent(userinput):
    """Handles ambient audio commands."""
    lower = userinput.lower()
    
    # Stop commands
    if "stop" in lower or "off" in lower:
        # Check if a specific sound is mentioned
        for kw, key in AUDIO_KEYWORDS.items():
            if kw in lower:
                return audio_service.stop_ambient(key)
        return audio_service.stop_all()
    
    # Volume command: "set rain to 40 percent"
    vol_match = re.search(r'(\d+)\s*(?:percent|%)', lower)
    sound_match = next((key for kw, key in AUDIO_KEYWORDS.items() if kw in lower), None)
    
    if vol_match and sound_match:
        vol = int(vol_match.group(1)) / 100
        return audio_service.set_volume(sound_match, vol)
    
    # Play commands
    if sound_match:
        return audio_service.play_ambient(sound_match)
    
    return "Which sound should I play? Try: rain, café, forest, ocean, white noise."

def handle_workspace_intent(userinput):
    """Handles workspace launch commands."""
    from src.services.workspace_service import workspace_service
    config = workspace_service._load_config()
    
    for ws_name in config.keys():
        if ws_name.lower() in userinput.lower():
            return workspace_service.launch_workspace(ws_name)
    
    return f"Available workspaces: {', '.join(config.keys())}. Which one should I open?"

def handle_finance_intent(userinput):
    """Parses natural language and logs a transaction to finance.csv."""
    amount = extract_amount(userinput)
    category, trans_type = categorize_expense(userinput)
    description = userinput.strip()
    return finance_service.log_transaction(amount, category, description, trans_type)