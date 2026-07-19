import tkinter as tk
from tkinter import ttk
import time
import threading


class FocusModeUI:
    """
    Live Focus Mode tab — shows a ticking countdown, phase label,
    a circular SVG-style progress arc, and Pause / +5 Min / End controls.
    Communicates with TimerService via the shared active_timers dict.
    """

    # Phase colours
    FOCUS_COLOR  = "#FF5733"   # warm orange-red
    BREAK_COLOR  = "#4CAF50"   # green
    BG           = "#36454F"
    FG           = "#FEFCFB"
    BTN_BG       = "#2C3840"

    # Static session count across transitions in the same UI instance
    session_count = 1

    def __init__(self, parent, timer_service):
        self.parent       = parent
        self.timer_service = timer_service
        self._running     = True
        self._paused      = False
        self._pause_remaining = None
        self._timer_id    = None   # resolved on first tick

        self._completed = False  # True once the timer finishes
        self._last_focus_mins = 25 # Fallback
        self._build_ui()
        self._start_tick()
        # Subscribe to timer-complete notification
        from src.core.event_bus import bus as _bus
        _bus.subscribe("ui.timer_complete", self._handle_timer_complete_event)

    # ------------------------------------------------------------------ #
    #  UI construction                                                     #
    # ------------------------------------------------------------------ #

    def _build_ui(self):
        self.parent.config(bg=self.BG)

        # Find current session type
        active = self.timer_service.get_all_active()
        name = active[0]["name"] if active else "Focus"
        color = self.FOCUS_COLOR if name == "Focus" else self.BREAK_COLOR

        # Header with Total Focused Today
        stats_frame = tk.Frame(self.parent, bg=self.BG)
        stats_frame.pack(fill="x", padx=10, pady=(5, 0))
        
        total_mins = self.timer_service.get_total_focused_today()
        h = total_mins // 60
        m = total_mins % 60
        stats_text = f"Total Focused Today: {h}h {m}m"
        
        tk.Label(stats_frame, text=stats_text, font=("Segoe UI", 8),
                 bg=self.BG, fg="#90A4AE").pack(side="right")

        # Canvas for the arc progress ring
        self.canvas = tk.Canvas(self.parent, width=110, height=110,
                                bg=self.BG, highlightthickness=0)
        self.canvas.pack(pady=(5, 2))
        self._arc_bg  = self.canvas.create_arc(8, 8, 102, 102,
                                                start=90, extent=360,
                                                outline="#3d5260", width=6,
                                                style="arc")
        self._arc_fg  = self.canvas.create_arc(8, 8, 102, 102,
                                                start=90, extent=0,
                                                outline=color, width=6,
                                                style="arc", tags="arc")

        # Phase label (Focus Session X / Break Time)
        phase_txt = f"● FOCUS SESSION {FocusModeUI.session_count}" if name == "Focus" else "● BREAK TIME"
        self.phase_label = tk.Label(self.parent, text=phase_txt,
                                    font=("Segoe UI", 10, "bold"),
                                    bg=self.BG, fg=color)
        self.phase_label.pack()

        # Time label
        self.time_label = tk.Label(self.parent, text="--:--",
                                   font=("Segoe UI", 24, "bold"),
                                   bg=self.BG, fg=self.FG)
        self.time_label.pack()

        # Controls row
        btn_frame = tk.Frame(self.parent, bg=self.BG)
        btn_frame.pack(pady=5)

        self.pause_btn = tk.Button(btn_frame, text="⏸ Pause",
                                   command=self._toggle_pause,
                                   bg=self.BTN_BG, fg=self.FG,
                                   relief="flat", padx=8, pady=4,
                                   font=("Segoe UI", 9))
        self.pause_btn.grid(row=0, column=0, padx=4)

        if name == "Focus":
            add_btn = tk.Button(btn_frame, text="+5 Min",
                                command=self._add_five,
                                bg=self.BTN_BG, fg=self.FG,
                                relief="flat", padx=8, pady=4,
                                font=("Segoe UI", 9))
            add_btn.grid(row=0, column=1, padx=4)
        else:
            skip_btn = tk.Button(btn_frame, text="⏭ Skip",
                                command=self._skip_break,
                                bg=self.BTN_BG, fg=self.FG,
                                relief="flat", padx=8, pady=4,
                                font=("Segoe UI", 9))
            skip_btn.grid(row=0, column=1, padx=4)

        # End session button
        end_btn = tk.Button(self.parent, text="■ End Session",
                            command=self._end_session,
                            bg="#5C2020", fg=self.FG,
                            relief="flat", padx=8, pady=4,
                            font=("Segoe UI", 9))
        end_btn.pack(pady=5)

    # ------------------------------------------------------------------ #
    #  Live tick                                                           #
    # ------------------------------------------------------------------ #

    def _start_tick(self):
        def tick():
            while self._running:
                if not self._paused:
                    self._update_display()
                time.sleep(1)

        threading.Thread(target=tick, daemon=True).start()

    def _update_display(self):
        """Pulls remaining time from the active timer and refreshes widgets."""
        if self._completed:
            return

        # Find the first active timer (could be Focus or Break)
        active = self.timer_service.get_all_active()
        if not active:
            return

        entry       = active[0]
        self._timer_id   = entry["id"]
        remaining   = entry["remaining"]
        name        = entry["name"]
        
        # Get total duration from the service
        with self.timer_service.lock:
            if self._timer_id in self.timer_service.active_timers:
                total_secs = self.timer_service.active_timers[self._timer_id]["total_duration"]
                if name == "Focus":
                    self._last_focus_mins = total_secs // 60
            else:
                return

        mins = int(remaining // 60)
        secs = int(remaining % 60)
        time_str = f"{mins:02d}:{secs:02d}"

        percent  = remaining / total_secs if total_secs > 0 else 0
        extent   = -360 * percent
        color    = self.FOCUS_COLOR if name == "Focus" else self.BREAK_COLOR
        phase_txt = f"● FOCUS SESSION {FocusModeUI.session_count}" if name == "Focus" else "● BREAK TIME"

        def _gui_update():
            try:
                self.time_label.config(text=time_str)
                self.phase_label.config(text=phase_txt, fg=color)
                self.canvas.itemconfig(self._arc_fg, extent=extent, outline=color)
            except:
                pass

        self.parent.after(0, _gui_update)

    # ------------------------------------------------------------------ #
    #  Controls                                                            #
    # ------------------------------------------------------------------ #

    def _toggle_pause(self):
        if not self._paused:
            active = self.timer_service.get_all_active()
            if active:
                self._timer_id = active[0]["id"]
                self.timer_service.pause_timer(self._timer_id)
            self._paused = True
            self.pause_btn.config(text="▶ Resume")
        else:
            if self._timer_id:
                self.timer_service.resume_timer(self._timer_id)
            self._paused = False
            self.pause_btn.config(text="⏸ Pause")

    def _add_five(self):
        active = self.timer_service.get_all_active()
        if active:
            tid = active[0]["id"]
            self.timer_service.add_time(tid, 300)

    def _skip_break(self):
        """Stop break and start focus again."""
        active = self.timer_service.get_all_active()
        if active:
            tid = active[0]["id"]
            with self.timer_service.lock:
                if tid in self.timer_service.active_timers:
                    del self.timer_service.active_timers[tid]
        self._start_focus()

    def _end_session(self):
        """Stop the timer and close the tab."""
        active = self.timer_service.get_all_active()
        if active:
            tid = active[0]["id"]
            with self.timer_service.lock:
                if tid in self.timer_service.active_timers:
                    del self.timer_service.active_timers[tid]
        self._running = False
        self.timer_service.focus_tab_dismissed = True
        FocusModeUI.session_count = 1

    # ------------------------------------------------------------------ #
    #  Completion screen                                                   #
    # ------------------------------------------------------------------ #

    def _handle_timer_complete_event(self, name="Focus", *args):
        """Bus event callback — schedule on the main thread."""
        self.parent.after(0, lambda: self._on_timer_complete(name))

    def _on_timer_complete(self, name="Focus"):
        """Replace the live timer UI with a 'Session Complete' screen."""
        if self._completed:
            return
        self._completed = True

        # Hide the running controls
        for widget in self.parent.winfo_children():
            widget.pack_forget()

        BG = self.BG
        FG = self.FG
        GREEN = self.BREAK_COLOR
        ORANGE = self.FOCUS_COLOR

        # Completion banner
        icon = "✅" if name == "Focus" else "☕"
        title = "Focus Complete!" if name == "Focus" else "Break Complete!"
        msg = "Great work. Take a breather." if name == "Focus" else "Ready for more?"
        color = GREEN if name == "Focus" else ORANGE

        tk.Label(self.parent, text=icon, font=("Segoe UI", 28),
                 bg=BG, fg=color).pack(pady=(16, 2))
        tk.Label(self.parent, text=title,
                 font=("Segoe UI", 14, "bold"),
                 bg=BG, fg=FG).pack()
        tk.Label(self.parent, text=msg,
                 font=("Segoe UI", 9),
                 bg=BG, fg="#90A4AE").pack(pady=(2, 12))

        btn_frame = tk.Frame(self.parent, bg=BG)
        btn_frame.pack()

        # Logic for 'Continue' button: Start break if Focus finished, start Focus if Break finished
        continue_cmd = self._start_break if name == "Focus" else self._start_focus
        
        tk.Button(btn_frame, text="▶ Continue",
                  command=continue_cmd,
                  bg=color, fg="#000000",
                  relief="flat", padx=10, pady=5,
                  font=("Segoe UI", 10, "bold")).grid(row=0, column=0, padx=6)

        tk.Button(btn_frame, text="■ Close",
                  command=self._dismiss,
                  bg=self.BTN_BG, fg=FG,
                  relief="flat", padx=10, pady=5,
                  font=("Segoe UI", 10)).grid(row=0, column=1, padx=6)

    def _start_break(self):
        """Transition to break mode."""
        # Calculate break: 5 mins or 1/5th of focus (max 10 mins as per requirement)
        calculated_break = self._last_focus_mins // 5
        break_mins = min(calculated_break, 10)
        if break_mins < 1: break_mins = 5 # Default if focus was very short
        
        # Start the break timer via service
        self.timer_service.start_timer("Break", break_mins)
        
        # Reset UI state
        self._completed = False
        self._paused = False
        
        # Clear completion screen and rebuild main UI
        for widget in self.parent.winfo_children():
            widget.destroy()
            
        self._build_ui()

    def _start_focus(self):
        """Transition back to focus mode."""
        FocusModeUI.session_count += 1
        
        # Start the focus timer via service (use last focus duration)
        self.timer_service.start_timer("Focus", self._last_focus_mins)
        
        # Reset UI state
        self._completed = False
        self._paused = False
        
        # Clear completion screen and rebuild main UI
        for widget in self.parent.winfo_children():
            widget.destroy()
            
        self._build_ui()

    def _dismiss(self):
        """Signal the monitor thread that the tab can be removed."""
        self._running = False
        self.timer_service.focus_tab_dismissed = True
        FocusModeUI.session_count = 1
