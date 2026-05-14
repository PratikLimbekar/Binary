import tkinter as tk
from tkinter import scrolledtext
from tkinter import ttk 
import threading
import logging
import datetime
import os
import keyboard

# Modular imports
from src.core.router import route_command
from src.services.db_service import insert_chatlog
from src.services.rag_service import addJSONtoRAGdb
from src.utils import voice_engine as voice
from src.core.event_bus import bus

# Setup logging to the logs directory
LOG_FILE = os.path.join(os.path.dirname(__file__), '..', '..', 'logs', 'aipp_chat_log.txt')
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - USER: %(message)s',
    datefmt='%d-%m-%Y %H: %M: %S'
)

# State variables
ttsenabled = True
collapseafterid = None
stayactive = False
active_tabs = {} # Track dynamic tabs

# Original Fonts and Colors
FONT_MAIN = ("Segoe UI", 10)
FONT_AI = ("Comic Sans MS", 12)
COLOR_ROOT = "#353935"
COLOR_BUTTON = "#36454F"
COLOR_FG = "#FEFCFB"

def sendmessage():
    """Handles the button click event."""
    input_text = user_entry.get()
    if input_text:
        print('input obtained.')
        sendbutton.config(state='disabled')
        response_label.grid(row=9, column=0, columnspan=2, sticky="w")
        response_label.config(text="Thinking...")
        root.update_idletasks()
        user_entry.delete(0, tk.END)
        threading.Thread(target=handle_ai_response, args=(input_text,)).start()

def handle_ai_response(input_text):
    """Calls Gemini and updates UI."""
    chatlog_dict = {}
    response = route_command(input_text)
    
    if response:
        def update_ui():
            response_label.config(text=response)
            response_label.grid(row=9, column=0, columnspan=2, sticky="w")
            exitbutton.grid(row=9, column=2, sticky="e")
            sendbutton.config(state='normal')
        root.after(0, update_ui)

        logging.info(input_text)
        chatlog_dict['input'] = input_text
        logging.info("AIPP: " + response)
        chatlog_dict['output'] = response
        chatlog_dict['timestamp'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        insert_chatlog(chatlog_dict)
        addJSONtoRAGdb(chatlog_dict)
        return response
    else:
        collapse_gui()
        return None

def blinktimer():
    """Original blink logic."""
    eye1_canvas.itemconfig(eye1_id, fill='black')
    eye2_canvas.itemconfig(eye2_id, fill='black')
    root.after(1001, blinktimer)

def trigger_assistant():
    """Triggers the voice input sequence."""
    root.after(0, lambda: [expand_ui(), cancelscheduledcollapse()])
    userinput = voice.listentouser()
    if userinput:
        response_label.config(text=userinput)
        response_label.grid(row=9, column=0, columnspan=2, sticky="w")
        exitbutton.grid(row=9, column=2, sticky="e")
        sendbutton.config(state='normal')
        response = handle_ai_response(userinput)
        if ttsenabled:
            voice.speakresponse(response)
        root.after(1500, schedule_collapse)

def voicethread():
    """Checks for hotword detection."""
    while True:
        if voice.detect_hotword():
            trigger_assistant()
        else:
            import time
            time.sleep(5) 

keyboard.add_hotkey('alt+shift+b', trigger_assistant)

def expand_ui(event=None):
    root.overrideredirect(False)
    sendframe.grid()
    chatframe.grid()
    notebook.grid()
    root.update_idletasks()
    root.geometry("")

def collapse_gui(event=None):
    for widget in [sendframe, chatframe, notebook, response_label]:
        widget.grid_remove()
    root.update_idletasks()
    root.overrideredirect(True)
    root.geometry("")

def schedule_collapse():
    global collapseafterid
    if stayactive: return
    if collapseafterid: root.after_cancel(collapseafterid)
    collapseafterid = root.after(3000, collapse_gui)

def cancelscheduledcollapse(event=None):
    global collapseafterid
    if collapseafterid:
        root.after_cancel(collapseafterid)
        collapseafterid = None

def togglestay():
    global stayactive
    stayactive = not stayactive
    staybutton.config(text="Stay: ON" if stayactive else "Stay: OFF", bg="#000000" if stayactive else COLOR_BUTTON)
    if not stayactive: schedule_collapse()

def toggletts():
    global ttsenabled
    ttsenabled = not ttsenabled
    tts.config(text="TTS: ON" if ttsenabled else "TTS: OFF")

def clear_response():
    response_label.grid_forget()
    exitbutton.grid_forget()

def add_mode_tab(name, create_func):
    """Dynamically adds a tab for a specific mode."""
    if name in active_tabs:
        notebook.select(active_tabs[name])
        return
    
    tab_frame = tk.Frame(notebook, bg=COLOR_BUTTON)
    create_func(tab_frame)
    notebook.add(tab_frame, text=name)
    active_tabs[name] = tab_frame
    notebook.select(tab_frame)
    expand_ui()

def remove_mode_tab(name):
    """Removes a dynamic tab."""
    if name in active_tabs:
        notebook.forget(active_tabs[name])
        del active_tabs[name]

def update_progress_border(percent, color="#FF5733"):
    """Draws a circular progress ring around the eyes."""
    # Clear previous ring
    eye1_canvas.delete("progress")
    eye2_canvas.delete("progress")
    
    if percent <= 0: return
    
    extent = -360 * (percent / 100)
    # Draw arc on both eyes for symmetry
    eye1_canvas.create_arc(2, 2, 28, 28, start=90, extent=extent, outline=color, width=2, style="arc", tags="progress")
    eye2_canvas.create_arc(2, 2, 28, 28, start=90, extent=extent, outline=color, width=2, style="arc", tags="progress")

root = tk.Tk()
root.configure(bg=COLOR_ROOT)
root.attributes('-topmost', True)
root.overrideredirect(True)

style = ttk.Style()
style.theme_use('clam')
style.configure('TNotebook', background=COLOR_BUTTON, borderwidth=0)
style.configure("TNotebook.Client", background=COLOR_BUTTON)
style.configure('TNotebook.Tab', background=COLOR_BUTTON, foreground=COLOR_FG, padding=[10,5])
style.map('TNotebook.Tab', background=[('selected', '#151b1f')])

notebook = ttk.Notebook(root)
notebook.grid(row=2, column=0, columnspan=3, sticky="nsew")
chat_tab = tk.Frame(notebook, bg=COLOR_BUTTON)
notebook.add(chat_tab, text="Chat")

eyeframe = tk.Frame(root, bg='#7692ff')
eyeframe.grid(row=0, column=0, columnspan=3)

eye1_canvas = tk.Canvas(eyeframe, width=30, height=30, bg='#36454f', highlightthickness=0)
eye1_canvas.grid(column=1, row=0)
eye1_canvas.create_oval(3, 3, 27, 27, fill='#fefcfb', outline='')
eye1_id = eye1_canvas.create_oval(5, 5, 25, 25, fill='#000000')

eye2_canvas = tk.Canvas(eyeframe, width=30, height=30, bg='#151b1f', highlightthickness=0)
eye2_canvas.grid(column=2, row=0)
eye2_canvas.create_oval(3, 3, 27, 27, fill='#fefcfb', outline='')
eye2_id = eye2_canvas.create_oval(5, 5, 25, 25, fill='#000000')

chatframe = tk.Frame(chat_tab, bg=COLOR_BUTTON)
chatframe.grid(row=0, column=0, columnspan=3)
response_label = tk.Label(chatframe, text="", font=FONT_AI, wraplength=250, bg=COLOR_BUTTON, fg=COLOR_FG, padx=10, pady=5)
exitbutton = tk.Button(chatframe, text='x', command=clear_response, bg=COLOR_BUTTON, fg=COLOR_FG)

sendframe = tk.Frame(chat_tab, bg=COLOR_BUTTON)
sendframe.grid(row=1, column=0, columnspan=3, pady=5)
user_entry = tk.Entry(sendframe)
user_entry.grid(column=0, row=0, padx=5)
sendbutton = tk.Button(sendframe, text="Send", command=sendmessage, bg=COLOR_BUTTON, fg=COLOR_FG)
sendbutton.grid(row=0, column=1)
tts = tk.Button(sendframe, text="TTS: ON", command=toggletts, bg=COLOR_BUTTON, fg=COLOR_FG)
tts.grid(row=0, column=2)
staybutton = tk.Button(sendframe, text="Stay: OFF", command=togglestay, bg=COLOR_BUTTON, fg=COLOR_FG)
staybutton.grid(column=0, row=1, columnspan=3, pady=5)

user_entry.bind("<Return>", lambda e: sendmessage())
eye1_canvas.bind("<Button-1>", expand_ui)
eye2_canvas.bind("<Button-1>", expand_ui)

# Subscribe to events
bus.subscribe("ui.add_tab", lambda name, func: root.after(0, lambda: add_mode_tab(name, func)))
bus.subscribe("ui.remove_tab", lambda name: root.after(0, lambda: remove_mode_tab(name)))
bus.subscribe("ui.update_progress", lambda p, c="#FF5733": root.after(0, lambda: update_progress_border(p, c)))
bus.subscribe("ui.execute", lambda func: root.after(0, func))

threading.Thread(target=voicethread, daemon=True).start()
blinktimer()
root.mainloop()
