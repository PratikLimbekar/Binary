import tkinter as tk
from tkinter import ttk
import threading
import logging
import os
import time
import re
import queue
import keyboard

# Modular imports
from src.core.router import route_command
from src.utils import voice_engine as voice
from src.core.event_bus import bus
from src.gui.scrollable_notebook import ScrollableNotebook
from src.modes.sticky_notes_ui import StickyNotesUI
from src.services.sticky_note_service import sticky_note_service

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
is_window_focused = False # Track if the app window has focus



# ── Helpers ───────────────────────────────────────────────────────────────────

# Thread-safe queue for cross-thread UI callbacks.
# Background threads enqueue callables here instead of calling root.after(),
# which is not safe when Tkinter is driven via root.update() in an asyncio loop.
_ui_queue: queue.SimpleQueue = queue.SimpleQueue()


def _safe_after(func):
    """Schedule func on the main thread — safe to call from ANY thread."""
    _ui_queue.put_nowait(func)


def drain_ui_queue():
    """Drain all pending UI callbacks. Must be called from the main thread."""
    try:
        while True:
            func = _ui_queue.get_nowait()
            try:
                func()
            except Exception as _e:
                logging.exception("Error in queued UI callback: %s", _e)
    except queue.Empty:
        pass


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
            threading.Thread(target=voice.speak_response, args=(text,), daemon=True).start()
        
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

    # Only start listening if Chat tab is active
    try:
        if notebook.tab(notebook.select(), "text") != "Chat":
            return
    except:
        return

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
    root.focus_force()


def collapse_gui(event=None):
    for widget in (sendframe, chatframe, notebook, response_label):
        widget.grid_remove()
    root.update_idletasks()
    root.overrideredirect(True)
    root.geometry("")


def schedule_collapse(delay_ms=None):
    global collapseafterid
    if stayactive or is_window_focused:
        return
    if collapseafterid:
        root.after_cancel(collapseafterid)
    
    wait_time = delay_ms if delay_ms is not None else COLLAPSE_DELAY_MS
    collapseafterid = root.after(wait_time, collapse_gui)


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

notebook = ScrollableNotebook(root)
notebook.grid(row=2, column=0, columnspan=3, sticky="nsew")

chat_tab = tk.Frame(notebook, bg=COLOR_BUTTON)
notebook.add(chat_tab, text="Chat")

# ── Sticky Notes Startup & Setup ──────────────────────────────────────────────
sticky_notes_ui = None
sticky_tab = None

def open_sticky_notes():
    global sticky_notes_ui, sticky_tab
    sticky_note_service.set_tab_visible(True)
    if "Sticky Notes" not in active_tabs:
        sticky_tab = tk.Frame(notebook, bg=COLOR_BUTTON)
        sticky_notes_ui = StickyNotesUI(sticky_tab)
        sticky_notes_ui.pack(fill="both", expand=True)
        notebook.add(sticky_tab, text="Sticky Notes")
        active_tabs["Sticky Notes"] = sticky_tab
    notebook.select(active_tabs["Sticky Notes"])
    expand_ui()


# ── Scheduler Window ───────────────────────────────────────────────────────────
_scheduler_window = None

def open_scheduler():
    """Opens the Scheduler as a standalone Toplevel window."""
    global _scheduler_window
    try:
        # If window already exists and is still open, just bring it to front
        if _scheduler_window and _scheduler_window.winfo_exists():
            _scheduler_window.lift()
            _scheduler_window.focus_force()
            return
    except Exception:
        pass

    try:
        import sys, os
        # Ensure the Binary root (parent of scheduler/) is on the path
        binary_root = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
        if binary_root not in sys.path:
            sys.path.insert(0, binary_root)

        from scheduler.ui.scheduler_window import SchedulerWindow
        _scheduler_window = SchedulerWindow(parent=root)
        _scheduler_window.lift()
        _scheduler_window.focus_force()
    except Exception as e:
        logging.exception("Failed to open Scheduler window: %s", e)
        import tkinter.messagebox as mb
        mb.showerror("Scheduler Error", f"Could not open the Scheduler:\n{e}")

if sticky_note_service.is_tab_visible():
    sticky_tab = tk.Frame(notebook, bg=COLOR_BUTTON)
    sticky_notes_ui = StickyNotesUI(sticky_tab)
    sticky_notes_ui.pack(fill="both", expand=True)
    notebook.add(sticky_tab, text="Sticky Notes")
    active_tabs["Sticky Notes"] = sticky_tab

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

def on_focus_in(event=None):
    """When app gains focus, cancel auto-minimization."""
    global is_window_focused
    is_window_focused = True
    cancelscheduledcollapse()

def on_focus_out(event=None):
    """When app loses focus, schedule minimization."""
    # Small delay to ensure focus hasn't just moved to another widget inside the app
    root.after(100, _check_real_focus_loss)

def _check_real_focus_loss():
    global is_window_focused
    if not root.focus_get():
        is_window_focused = False
        if voice.is_speaking:
            threading.Thread(target=_wait_for_tts_and_collapse, daemon=True).start()
        else:
            # Instant minimize if idle or just thinking/listening without TTS
            schedule_collapse(delay_ms=0)

def _wait_for_tts_and_collapse():
    """Wait for TTS to finish, then wait 2 more seconds before collapsing."""
    while voice.is_speaking:
        time.sleep(0.5)
    # User requested 2 seconds delay after TTS stops
    time.sleep(2)
    # Re-check focus before final collapse
    if not is_window_focused:
        _safe_after(collapse_gui)

user_entry.bind("<Return>", lambda e: sendmessage())
user_entry.bind("<KeyPress>", on_text_entry)
eye1_canvas.bind("<Button-1>", on_minimize_click)
eye2_canvas.bind("<Button-1>", on_minimize_click)
root.bind("<FocusIn>", on_focus_in)
root.bind("<FocusOut>", on_focus_out)

# ── Event Bus ─────────────────────────────────────────────────────────────────

bus.subscribe("ui.add_tab",         lambda name, func: _safe_after(lambda: add_mode_tab(name, func)))
bus.subscribe("ui.remove_tab",      lambda name:       _safe_after(lambda: remove_mode_tab(name)))
bus.subscribe("ui.update_progress", lambda p, c="#FF5733": _safe_after(lambda: update_progress_border(p, c)))
bus.subscribe("ui.timer_complete",  lambda *args:      _safe_after(expand_ui))
bus.subscribe("ui.reminder_triggered", lambda text: _safe_after(lambda: [
    expand_ui(),
    response_label.config(text=f"🔔 REMINDER: {text}"),
    response_label.grid(row=0, column=0, columnspan=2, sticky="w"),
    exitbutton.grid(row=0, column=2, sticky="e")
]))
bus.subscribe("ui.execute",         lambda func:       _safe_after(func))
bus.subscribe("ui.open_sticky_notes", lambda: _safe_after(open_sticky_notes))
bus.subscribe("ui.open_scheduler",  lambda: _safe_after(open_scheduler))

# ── Start ─────────────────────────────────────────────────────────────────────

def on_app_close():
    try:
        if sticky_notes_ui:
            sticky_notes_ui.save_current_note()
        sticky_note_service.save_state()
    except Exception as e:
        print(f"Error saving sticky note on exit: {e}")
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_app_close)

threading.Thread(target=voicethread, daemon=True).start()
blinktimer()
collapse_gui() # Ensure we start minimized
# root.mainloop() # Driven asynchronously from desktop/src/main.py