import tkinter as tk
from tkinter import ttk
import threading
import logging
import os
import time
import re
import keyboard

# Modular imports
from src.core.router import route_command
from src.utils import voice_engine as voice
from src.core.event_bus import bus

# ── Logging ──────────────────────────────────────────────────────────────────
LOG_FILE = os.path.join(os.path.dirname(__file__), '..', '..', 'logs', 'aipp_chat_log.txt')
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%d-%m-%Y %H:%M:%S',   # FIX: removed stray spaces in original format
)

# ── Constants ─────────────────────────────────────────────────────────────────
FONT_MAIN = ("Segoe UI", 10)
FONT_AI   = ("Comic Sans MS", 12)
COLOR_ROOT   = "#353935"
COLOR_BUTTON = "#36454F"
COLOR_FG     = "#FEFCFB"

COLLAPSE_DELAY_MS = 3000  # centralise magic numbers

# ── State ─────────────────────────────────────────────────────────────────────
ttsenabled      = True
stayactive      = False
collapseafterid = None
active_tabs: dict = {}
is_thinking = False
spinner_angle = 0
is_listening = False  # Track if voice listening is active


# ── Helpers ───────────────────────────────────────────────────────────────────

def _safe_after(func):
    """Schedule func on the main thread — safe to call from any thread."""
    root.after(0, func)


# ── UI Actions ────────────────────────────────────────────────────────────────

def sendmessage():
    """Handle the Send button / Enter key."""
    global is_listening
    is_listening = False  # Stop listening when user sends a message
    input_text = user_entry.get().strip()
    if not input_text:
        return
    sendbutton.config(state='disabled')
    response_label.grid(row=0, column=0, columnspan=2, sticky="w")
    response_label.config(text="Thinking…")
    user_entry.delete(0, tk.END)
    root.update_idletasks()
    threading.Thread(target=handle_ai_response, args=(input_text,), daemon=True).start()


def handle_ai_response(input_text: str):
    """Run in a background thread; shows a spinner instead of streaming."""
    global is_thinking, is_listening
    is_listening = False  # Stop listening when model starts processing
    try:
        is_thinking = True
        _safe_after(start_spinner)
        _safe_after(lambda: response_label.config(text="[SYNCING] Sending to Brain..."))
        
        result = route_command(input_text)
        
        _safe_after(lambda: response_label.config(text="[PROCESSING] Finalizing answer..."))
    except Exception as exc:
        is_thinking = True # Keep spinner for a second to show we're stopping
        error_msg = str(exc)
        logging.exception("route_command raised an exception")
        
        def _report_error():
            global is_thinking
            is_thinking = False
            _show_error(error_msg)
        
        _safe_after(_report_error)
        return

    is_thinking = False
    if not result:
        _safe_after(collapse_gui)
        return

    response, res_type = result
    prefix = f"[{res_type.upper()}] " if res_type != "chat" else ""

    # Clean up JSON if it leaks in static chat
    final_text = str(response)
    final_text = re.sub(r'\{.*?"response":\s*"(.*?)"\}', r'\1', final_text, flags=re.DOTALL)
    final_text = final_text.replace('{"type":"chat","response":"', '').replace('"}', '').strip('"{ }')
    
    final_display = prefix + final_text
    _safe_after(lambda: response_label.config(text=final_display))

    # ── Finalise UI on main thread ────────────────────────────────────────────
    def _finalise(text=final_text):
        response_label.grid(row=0, column=0, columnspan=2, sticky="w")
        exitbutton.grid(row=0, column=2, sticky="e")
        sendbutton.config(state='normal')
        if ttsenabled:
            threading.Thread(target=voice.speakresponse, args=(text,), daemon=True).start()
        
        # Start the countdown to minimize only after the response is shown
        root.after(1000, schedule_collapse)

    _safe_after(_finalise)

    logging.info("USER: %s", input_text)
    logging.info("BINARY: %s", final_text)


def _show_error(msg: str):
    response_label.config(text=f"[ERROR] {msg}")
    response_label.grid(row=0, column=0, columnspan=2, sticky="w")
    sendbutton.config(state='normal')


# ── Eyes / Animation ──────────────────────────────────────────────────────────

_BLINK_CLOSE_MS = 150   # how long eyes stay shut
_BLINK_CYCLE_MS = 4000  # full blink period


def _blink_close():
    eye1_canvas.itemconfig(eye1_id, fill='black')
    eye2_canvas.itemconfig(eye2_id, fill='black')
    root.after(_BLINK_CLOSE_MS, _blink_open)


def _blink_open():
    # FIX: original blinktimer never re-opened the eyes
    eye1_canvas.itemconfig(eye1_id, fill='#000000')
    eye2_canvas.itemconfig(eye2_id, fill='#000000')
    root.after(_BLINK_CYCLE_MS, _blink_close)


def blinktimer():
    """Start the blink loop."""
    root.after(_BLINK_CYCLE_MS, _blink_close)


# ── Voice ─────────────────────────────────────────────────────────────────────

def trigger_assistant():
    """Called from hotkey or voice thread — schedules UI expand, then listens."""
    _safe_after(lambda: [expand_ui(), cancelscheduledcollapse()])
    userinput = voice.listentouser()
    if userinput:
        def _show_input():
            response_label.config(text=userinput)
            response_label.grid(row=0, column=0, columnspan=2, sticky="w")
            exitbutton.grid(row=0, column=2, sticky="e")
            sendbutton.config(state='normal')
        _safe_after(_show_input)
        handle_ai_response(userinput)
    else:
        # If no input or error, and user isn't typing, auto-minimize
        def _check_and_collapse():
            if not user_entry.get().strip():
                response_label.config(text="Could not understand...")
                schedule_collapse()
        _safe_after(_check_and_collapse)


def trigger_listening_on_minimize_click():
    """Called when minimized window is clicked - starts voice listening."""
    global is_listening
    # Only start listening if not already thinking and text box is empty
    if is_thinking or user_entry.get().strip():
        return
    
    is_listening = True
    response_label.config(text="Listening...")
    response_label.grid(row=0, column=0, columnspan=2, sticky="w")
    
    # Listen in a background thread
    def _listen_loop():
        global is_listening
        userinput = voice.listentouser()
        is_listening = False
        if userinput and not is_thinking:
            def _show_input():
                response_label.config(text=userinput)
                response_label.grid(row=0, column=0, columnspan=2, sticky="w")
                exitbutton.grid(row=0, column=2, sticky="e")
                sendbutton.config(state='normal')
            _safe_after(_show_input)
            handle_ai_response(userinput)
        else:
            # If no input or error, and user isn't typing, auto-minimize
            def _check_and_collapse():
                if not user_entry.get().strip():
                    response_label.config(text="Could not understand...")
                    schedule_collapse()
            _safe_after(_check_and_collapse)
    
    threading.Thread(target=_listen_loop, daemon=True).start()


def voicethread():
    """Hotword detection loop — runs in a daemon thread."""
    # FIX: import time at module level; no per-iteration import
    while True:
        if voice.detect_hotword():
            trigger_assistant()
        else:
            time.sleep(5)


keyboard.add_hotkey('alt+shift+b', lambda: threading.Thread(
    target=trigger_assistant, daemon=True).start()
)


# ── UI Expand / Collapse ──────────────────────────────────────────────────────

def expand_ui(event=None):
    root.overrideredirect(False)
    sendframe.grid()
    chatframe.grid()
    notebook.grid()
    root.update_idletasks()
    root.geometry("")


def collapse_gui(event=None):
    for widget in (sendframe, chatframe, notebook, response_label):
        widget.grid_remove()
    root.update_idletasks()
    root.overrideredirect(True)
    root.geometry("")


def schedule_collapse():
    global collapseafterid
    if stayactive:
        return
    if collapseafterid:
        root.after_cancel(collapseafterid)
    collapseafterid = root.after(COLLAPSE_DELAY_MS, collapse_gui)


def cancelscheduledcollapse(event=None):
    global collapseafterid
    if collapseafterid:
        root.after_cancel(collapseafterid)
        collapseafterid = None


# ── Toggle Buttons ────────────────────────────────────────────────────────────

def togglestay():
    global stayactive
    stayactive = not stayactive
    staybutton.config(
        text="Stay: ON" if stayactive else "Stay: OFF",
        bg="#000000" if stayactive else COLOR_BUTTON,
    )
    if not stayactive:
        schedule_collapse()


def toggletts():
    global ttsenabled
    ttsenabled = not ttsenabled
    tts_btn.config(text="TTS: ON" if ttsenabled else "TTS: OFF")


def clear_response():
    response_label.grid_forget()
    exitbutton.grid_forget()


# ── Dynamic Tabs ──────────────────────────────────────────────────────────────

def add_mode_tab(name: str, create_func):
    """Add (or focus) a named tab. Must be called on the main thread."""
    if name in active_tabs:
        notebook.select(active_tabs[name])
        return
    tab_frame = tk.Frame(notebook, bg=COLOR_BUTTON)
    create_func(tab_frame)
    notebook.add(tab_frame, text=name)
    active_tabs[name] = tab_frame
    notebook.select(tab_frame)
    expand_ui()


def remove_mode_tab(name: str):
    """Remove a named tab. Must be called on the main thread."""
    if name in active_tabs:
        notebook.forget(active_tabs[name])
        del active_tabs[name]


# ── Progress Ring ─────────────────────────────────────────────────────────────

def start_spinner():
    """Starts the circular loading animation."""
    global spinner_angle
    if not is_thinking:
        for canvas in (eye1_canvas, eye2_canvas):
            canvas.delete("spinner")
        return
    
    spinner_angle = (spinner_angle + 20) % 360
    for canvas in (eye1_canvas, eye2_canvas):
        canvas.delete("spinner")
        canvas.create_arc(2, 2, 28, 28, start=spinner_angle, extent=60, outline="#7692ff", width=3, style="arc", tags="spinner")
    
    root.after(50, start_spinner)

def update_progress_border(percent: float, color: str = "#FF5733"):
    """Draw a circular progress arc around both eye canvases."""
    for canvas in (eye1_canvas, eye2_canvas):
        canvas.delete("progress")
    if percent <= 0:
        return
    extent = -360 * (percent / 100)
    for canvas in (eye1_canvas, eye2_canvas):
        canvas.create_arc(
            2, 2, 28, 28,
            start=90, extent=extent,
            outline=color, width=2,
            style="arc", tags="progress",
        )


# ── Root Window ───────────────────────────────────────────────────────────────

root = tk.Tk()
root.configure(bg=COLOR_ROOT)
root.attributes('-topmost', True)
root.overrideredirect(True)

# ── Notebook / Tabs ───────────────────────────────────────────────────────────

style = ttk.Style()
style.theme_use('clam')
style.configure('TNotebook', background=COLOR_BUTTON, borderwidth=0)
style.configure('TNotebook.Client', background=COLOR_BUTTON)
style.configure('TNotebook.Tab', background=COLOR_BUTTON, foreground=COLOR_FG, padding=[10, 5])
style.map('TNotebook.Tab', background=[('selected', '#151b1f')])

notebook = ttk.Notebook(root)
notebook.grid(row=2, column=0, columnspan=3, sticky="nsew")

chat_tab = tk.Frame(notebook, bg=COLOR_BUTTON)
notebook.add(chat_tab, text="Chat")

# ── Eyes ──────────────────────────────────────────────────────────────────────

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

# ── Chat Frame ────────────────────────────────────────────────────────────────

chatframe = tk.Frame(chat_tab, bg=COLOR_BUTTON)
chatframe.grid(row=0, column=0, columnspan=3)

response_label = tk.Label(
    chatframe, text="", font=FONT_AI,
    wraplength=250, bg=COLOR_BUTTON, fg=COLOR_FG,
    padx=10, pady=5,
)
exitbutton = tk.Button(
    chatframe, text='x', command=clear_response,
    bg=COLOR_BUTTON, fg=COLOR_FG,
)

# ── Send Frame ────────────────────────────────────────────────────────────────

sendframe = tk.Frame(chat_tab, bg=COLOR_BUTTON)
sendframe.grid(row=1, column=0, columnspan=3, pady=5)

user_entry = tk.Entry(sendframe)
user_entry.grid(column=0, row=0, padx=5)

sendbutton = tk.Button(sendframe, text="Send", command=sendmessage, bg=COLOR_BUTTON, fg=COLOR_FG)
sendbutton.grid(row=0, column=1)

tts_btn = tk.Button(sendframe, text="TTS: ON", command=toggletts, bg=COLOR_BUTTON, fg=COLOR_FG)
tts_btn.grid(row=0, column=2)

minimize_btn = tk.Button(sendframe, text="−", command=collapse_gui, bg=COLOR_BUTTON, fg=COLOR_FG, font=("Segoe UI", 10, "bold"), width=3)
minimize_btn.grid(row=0, column=3, padx=2)

staybutton = tk.Button(sendframe, text="Stay: OFF", command=togglestay, bg=COLOR_BUTTON, fg=COLOR_FG)
staybutton.grid(column=0, row=1, columnspan=4, pady=5)

# ── Bindings ──────────────────────────────────────────────────────────────────

def on_minimize_click(event):
    """When minimized window (eyes) is clicked, expand UI and start listening for voice."""
    expand_ui()
    trigger_listening_on_minimize_click()

def on_text_entry(event):
    """When user starts typing, stop listening."""
    global is_listening
    is_listening = False

user_entry.bind("<Return>", lambda e: sendmessage())
user_entry.bind("<KeyPress>", on_text_entry)
eye1_canvas.bind("<Button-1>", on_minimize_click)
eye2_canvas.bind("<Button-1>", on_minimize_click)

# ── Event Bus ─────────────────────────────────────────────────────────────────

bus.subscribe("ui.add_tab",         lambda name, func: _safe_after(lambda: add_mode_tab(name, func)))
bus.subscribe("ui.remove_tab",      lambda name:       _safe_after(lambda: remove_mode_tab(name)))
bus.subscribe("ui.update_progress", lambda p, c="#FF5733": _safe_after(lambda: update_progress_border(p, c)))
bus.subscribe("ui.timer_complete",  lambda *args:      _safe_after(expand_ui))
bus.subscribe("ui.execute",         lambda func:       _safe_after(func))

# ── Start ─────────────────────────────────────────────────────────────────────

def start_app():
    threading.Thread(target=voicethread, daemon=True).start()
    blinktimer()
    collapse_gui() # Ensure we start minimized

if __name__ == "__main__":
    start_app()
    root.mainloop()