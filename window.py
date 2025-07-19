import tkinter as tk
from tkinter import scrolledtext
from tkinter import ttk #provides access to themed widgets, such as win11
import music
import pygame
from google import genai
import voice
import threading
import logging
from command_router import route_command
import mediacontrols

logging.basicConfig(
    filename='aipp_chat_log.txt',
    level=logging.INFO,
    format='%(asctime)s - USER: %(message)s',
    datefmt='%d-%m-%Y %H: %M: %S'
)

#initialise pygame
pygame.mixer.init()
isstaring = False
ttsenabled = True
collapseafterid = None #global var to track scheduled collapse
stayactive = False #stay active for window

#fonts and colors
FONT_MAIN = ("Segoe UI", 10)
FONT_AI = ("Comic Sans MS", 12)
COLOR_root = "#353935"
COLOR_BUTTON = "#36454F"
COLOR_FG = "#FEFCFB"

#this handles the button click event
def sendmessage():
    """
    creates a seperate thread to call handle_ai_response
    makes response label visible
    """
    input = user_entry.get()
    if input:
        print('input obtained.')
        sendbutton.config(state='disabled')
        response_label.grid(row=9, column=0, columnspan=2, sticky="w")
        response_label.config(text="Thinking...")
        response_label.grid(row=9, column=0)
        root.update_idletasks()
        user_entry.delete(0, tk.END)
        threading.Thread(target=handle_ai_response, args=(input,)).start()

def handle_ai_response(input):
    """
    calls getairesponse to get response from gemini
    updates response label with responded text
    returns response
    """
    response = route_command(input)
    if response:
        def update_ui():
            response_label.config(text=response)
            response_label.grid(row=9, column=0, columnspan=2, sticky="w")
            exitbutton.grid(row=9, column=2, sticky="e")
            sendbutton.config(state='normal')
        root.after(0, update_ui)
        logging.info(input)
        logging.info("AIPP: " + response)
        return response
    else:
        collapse_gui()
        return None

def blinktimer():
    """
    makes the eyes blink repeatedly after a fixed interval
    """
    if not music.is_playing and not isstaring:
        eye1_canvas.itemconfig(eye1_id, fill='black' if eye1_canvas.itemcget(eye1_id, "fill") == "#fefcfb" else "#fefcfb")
        eye2_canvas.itemconfig(eye2_id, fill='black' if eye2_canvas.itemcget(eye2_id, "fill") == "#fefcfb" else "#fefcfb")
    elif isstaring:
        eye1_canvas.itemconfig(eye1_id, fill='black')
        eye2_canvas.itemconfig(eye2_id, fill='black')
    root.after(1001, blinktimer)

def blink(event=None):
    """
    make blink when eye clicked
    """
    if not music.is_playing and not isstaring:
        eye1_canvas.itemconfig(eye1_id, fill='#fefcfb' if eye1_canvas.itemcget(eye1_id, "fill") == "black" else "black")
        eye2_canvas.itemconfig(eye2_id, fill='#fefcfb' if eye2_canvas.itemcget(eye2_id, "fill") == "black" else "black")
    else:
        eye1_canvas.itemconfig(eye1_id, fill='black')
        eye2_canvas.itemconfig(eye2_id, fill='black')

def look():
    """
    function to make the eyes stare
    """
    global isstaring
    isstaring = True

def voicethread():
    """
    checks if hotword detected and calls handle_ai_response if detected
    gets response back and speaks it.
    """
    global isstaring, ttsenabled, stayactive
    userinput = None       
    while True:
        if voice.detect_hotword():
            root.after(0, lambda: [set_stay(True), expand_ui(), cancelscheduledcollapse()])
            userinput = voice.listentouser()
        if userinput:
            response_label.config(text=userinput)
            response_label.grid(row=9, column=0, columnspan=2, sticky="w")
            exitbutton.grid(row=9, column=2, sticky="e")
            sendbutton.config(state='normal')
            print("user input obtained.")
            look()
            response = handle_ai_response(userinput)
            if ttsenabled:
                voice.speakresponse(response)
            isstaring = False
            # Wait a bit before disabling stay and triggering collapse
            def reset_stay():
                set_stay(False)
                schedule_collapse()
            root.after(1500, reset_stay)  # wait 5 seconds before collapsing

def set_stay(value: bool):
    """
    sets window staying active and expanded
    """
    global stayactive
    stayactive = value
    staybutton.config(text="Stay: ON" if value else "Stay: OFF")

def toggletts():
    """Toggles text to speech"""
    global ttsenabled
    ttsenabled = not ttsenabled
    tts.config(text="TTS: ON" if ttsenabled else "TTS: OFF")

def clearresponse():
    """clears response"""
    response_label.grid_forget()
    exitbutton.grid_forget()
    chatframe.grid_forget()
    # chat_box.grid_forget()

def expand_ui(event=None):
    """Expands UI"""
    root.overrideredirect(False)
    controlsframe.grid()
    sendframe.grid()
    chatframe.grid()
    notebook.grid()
    root.update_idletasks() #forces layout to update *before* resizing
    root.geometry("")

def collapse_gui(event=None):
    """Collapses UI"""
    for widget in [controlsframe, sendframe, chatframe, notebook, response_label]:
        widget.grid_remove()
    root.update_idletasks()
    root.overrideredirect(True)
    root.geometry("")

def schedule_collapse():
    """Collapses UI after a scheduled time by calling collapse_gui"""
    global collapseafterid
    if stayactive:
        return
    if collapseafterid is not None:
        root.after_cancel(collapseafterid)
    collapseafterid = root.after(3000, collapse_gui) #3second delay

def cancelscheduledcollapse(event=None):
    """Cancels scheduled collapse"""
    global collapseafterid
    if collapseafterid is not None:
        root.after_cancel(collapseafterid)
        collapseafterid = None

def togglestay():
    """Toggles constant expandedness"""
    global stayactive
    stayactive = not stayactive
    staybutton.config(text="Stay: ON" if stayactive else "Stay: OFF",
                      bg="#000000" if stayactive else "#36454f")
    
    if not stayactive:
        # If Stay is turned off, start collapse countdown
        schedule_collapse()

root = tk.Tk(screenName="Binary")
root.bind("<FocusOut>",lambda e: schedule_collapse())
root.bind("<FocusIn>", cancelscheduledcollapse)
root.configure(bg='#36454f')
root.attributes('-topmost', True)
root.overrideredirect(True) #removes window borders

#notebook to create and keep seperate tabs
notebook = ttk.Notebook(root, style='TNotebook', padding=0)
notebook.grid(row=2, column=0, columnspan=3, sticky="nsew")
notebook.configure(takefocus=0)

chat_tab = tk.Frame(notebook, bg='#36454f', borderwidth=0)
musictab = tk.Frame(notebook, bg='#36454f', borderwidth=0)

notebook.add(chat_tab, text="Chat")
notebook.add(musictab, text="Music")

style = ttk.Style()
style.theme_use('clam')
style.configure('TNotebook', background='#36454f', borderwidth=0, padding=0)
style.configure("TNotebook.Client", background="#36454f")

style.configure('TNotebook.Tab',
                background='#36454f',
                foreground='#fefcfb',
                padding=[10,5])
style.map('TNotebook.Tab',
          background=[('selected', '#151b1f')],
          foreground=[('selected', '#FEFCFB')])

style.layout("TNotebook", [
    ("Notebook.client", {"sticky": "nswe"})  # override default padding
])

for i in range(3):
    root.columnconfigure(i, weight=1)
for i in range(10):
    root.rowconfigure(i, weight=1)

controlsframe = tk.Frame(musictab, bg='#36454f')
controlsframe.grid(row=2, column=0, columnspan=3, pady=5)

sendframe = tk.Frame(chat_tab, bg='#36454f')
sendframe.grid(row=6, column=0, columnspan=3, pady=5)

chatframe = tk.Frame(chat_tab, bg="#36454f")
chatframe.grid(row=2, column=0, columnspan=3)

eyeframe = tk.Frame(root, bg='#7692ff')
eyeframe.grid(row=0, column=0, columnspan=3)

controlsframe.grid_remove()
sendframe.grid_remove()
chatframe.grid_remove()
notebook.grid_remove()


eye1_canvas = tk.Canvas(eyeframe, width=30, height=30, bg='#36454f', highlightthickness=0, )
eye1_canvas.grid(column=1, row=0)
# Outer white ring
eye1_canvas.create_oval(3, 3, 27, 27, fill='#fefcfb', outline='')  # white ring
eye1_id = eye1_canvas.create_oval(5, 5, 25, 25, fill='#fefcfb')

eye2_canvas = tk.Canvas(eyeframe, width=30, height=30, bg='#151b1f', highlightthickness=0)
eye2_canvas.grid(column=2, row=0)
# Outer white ring
eye2_canvas.create_oval(3, 3, 27, 27, fill='#fefcfb', outline='')  # white ring
eye2_id = eye2_canvas.create_oval(5, 5, 25, 25, fill='#fefcfb')

play = tk.Button(controlsframe, text="\u23EF\uFE0F", command=lambda: [mediacontrols.pausemusic()], bg="#36454f", fg="#fefcfb")
next = tk.Button(controlsframe, text="\u23ED\uFE0F", command=lambda: [mediacontrols.nexttrack()], bg="#36454f", fg="#fefcfb")
prev = tk.Button(controlsframe, text="\u23EA", command=lambda: [mediacontrols.prevtrack()], bg="#36454f", fg="#fefcfb")

play.grid(column=1, row=3)
next.grid(column=4, row=3)
prev.grid(column=0, row=3)

volumelabel = tk.Label(controlsframe, text="Volume", bg="#36454f", fg="#fefcfb")
volumeslider = ttk.Scale(controlsframe, from_=0, to=100, orient="horizontal", command=music.setvolume)
volumeslider.set(70)
volumelabel.grid(column=0, row=5)
volumeslider.grid(column=1, row=5, columnspan=2)

user_entry = tk.Entry(sendframe, selectbackground="#36454f", selectforeground="#fefcfb")
user_entry.grid(column=0, row=0, padx=5)
sendbutton = tk.Button(sendframe, text="Send", command=sendmessage, bg="#36454f", fg="#fefcfb")
tts = tk.Button(sendframe, text="TTS: ON", command=toggletts, bg="#36454f", fg="#fefcfb")

user_entry.bind("<Return>", lambda event: sendmessage())
sendbutton.grid(row=0, column=1)
tts.grid(row=0, column=2)

response_label = tk.Label(chatframe, text="", justify="left", font=FONT_AI, wraplength=250, bg='#36454f', fg="#fefcfb", padx=10, pady=5)

# chat_box.bind("<Button-1>", lambda event: on_chat_click(event))

exitbutton = tk.Button(chatframe, text='x', width=3, command=clearresponse, bg="#36454f", fg="#fefcfb")

staybutton = tk.Button(sendframe, text="Stay: OFF", command=togglestay, bg="#36454f", fg="#fefcfb")
staybutton.grid(column=0, row=1, columnspan=3, pady=5)

# eyeframe.bind("<B1-Motion>", domove)
eye1_canvas.bind("<Button-1>", expand_ui)
# eye1_canvas.bind("<B1-Motion>", domove)
eye2_canvas.bind("<Button-1>", expand_ui)
# eye2_canvas.bind("<B1-Motion>", domove)

root.columnconfigure(0, weight=1)
root.rowconfigure(7, weight=1)
chat_tab.rowconfigure(0, weight=1)
musictab.rowconfigure(0, weight=1)
root.resizable(True, True)


root.configure(bg='#353935')

def startbgtasks():
    threading.Thread(target=lambda: music.check_music_end(root), daemon=True).start()
    
threading.Thread(target=voicethread, daemon=True).start()
blinktimer()

root.mainloop()
root.after(100, startbgtasks)
