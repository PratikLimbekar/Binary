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

    def __init__(self, parent, timer_service):
        self.parent       = parent
        self.timer_service = timer_service
        self._running     = True
        self._paused      = False
        self._pause_remaining = None
        self._timer_id    = None   # resolved on first tick

        self._build_ui()
        self._start_tick()
        self._completed = False  # True once the timer finishes
        # Subscribe to timer-complete notification
        from src.core.event_bus import bus as _bus
        _bus.subscribe("ui.timer_complete", self._handle_timer_complete_event)

    # ------------------------------------------------------------------ #
    #  UI construction                                                     #
    # ------------------------------------------------------------------ #

    def _build_ui(self):
        self.parent.config(bg=self.BG)

        # Canvas for the arc progress ring
        self.canvas = tk.Canvas(self.parent, width=110, height=110,
                                bg=self.BG, highlightthickness=0)
        self.canvas.pack(pady=(12, 2))
        self._arc_bg  = self.canvas.create_arc(8, 8, 102, 102,
                                                start=90, extent=360,
                                                outline="#3d5260", width=6,
                                                style="arc")
        self._arc_fg  = self.canvas.create_arc(8, 8, 102, 102,
                                                start=90, extent=0,
                                                outline=self.FOCUS_COLOR, width=6,
                                                style="arc", tags="arc")

        # Phase label (FOCUS / BREAK)
        self.phase_label = tk.Label(self.parent, text="● FOCUS",
                                    font=("Segoe UI", 9, "bold"),
                                    bg=self.BG, fg=self.FOCUS_COLOR)
        self.phase_label.pack()

        # Time label drawn over the canvas (via place inside a Frame trick)
        self.time_label = tk.Label(self.parent, text="--:--",
                                   font=("Segoe UI", 22, "bold"),
                                   bg=self.BG, fg=self.FG)
        self.time_label.pack()

        # Session name
        self.session_label = tk.Label(self.parent, text="",
                                      font=("Segoe UI", 8),
                                      bg=self.BG, fg="#90A4AE")
        self.session_label.pack(pady=(0, 8))

        # Controls row
        btn_frame = tk.Frame(self.parent, bg=self.BG)
        btn_frame.pack()

        self.pause_btn = tk.Button(btn_frame, text="⏸ Pause",
                                   command=self._toggle_pause,
                                   bg=self.BTN_BG, fg=self.FG,
                                   relief="flat", padx=8, pady=4,
                                   font=("Segoe UI", 9))
        self.pause_btn.grid(row=0, column=0, padx=4)

        add_btn = tk.Button(btn_frame, text="+5 Min",
                            command=self._add_five,
                            bg=self.BTN_BG, fg=self.FG,
                            relief="flat", padx=8, pady=4,
                            font=("Segoe UI", 9))
        add_btn.grid(row=0, column=1, padx=4)

        # End session button
        end_btn = tk.Button(self.parent, text="■ End Session",
                            command=self._end_session,
                            bg="#5C2020", fg=self.FG,
                            relief="flat", padx=8, pady=4,
                            font=("Segoe UI", 9))
        end_btn.pack(pady=8)

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
            # Timer just ended — let _on_timer_complete handle it
            if not self._completed:
                self.parent.after(0, self._on_timer_complete)
            return

        entry       = active[0]
        self._timer_id   = entry["id"]
        remaining   = entry["remaining"]
        name        = entry["name"]
        total_secs  = self.timer_service.active_timers[self._timer_id]["total_duration"]

        mins = int(remaining // 60)
        secs = int(remaining % 60)
        time_str = f"{mins:02d}:{secs:02d}"

        # Arc extent: full circle (360°) when full, shrinks to 0 at end
        # tkinter arcs go counter-clockwise for negative extent
        percent  = remaining / total_secs if total_secs > 0 else 0
        extent   = -360 * percent
        color    = self.FOCUS_COLOR if name == "Focus" else self.BREAK_COLOR
        phase_txt = f"● {name.upper()}"

        def _gui_update():
            self.time_label.config(text=time_str)
            self.session_label.config(text=name)
            self.phase_label.config(text=phase_txt, fg=color)
            self.canvas.itemconfig(self._arc_fg, extent=extent, outline=color)

        self.parent.after(0, _gui_update)

    # ------------------------------------------------------------------ #
    #  Controls                                                            #
    # ------------------------------------------------------------------ #

    def _toggle_pause(self):
        if not self._paused:
            # Pause: record remaining, freeze end_time
            active = self.timer_service.get_all_active()
            if active:
                self._timer_id        = active[0]["id"]
                self._pause_remaining = active[0]["remaining"]
                # Extend end_time infinitely so the run_timer thread waits
                self.timer_service.active_timers[self._timer_id]["end_time"] = float("inf")
            self._paused = True
            self.pause_btn.config(text="▶ Resume")
        else:
            # Resume: restore end_time from remaining
            if self._timer_id and self._timer_id in self.timer_service.active_timers:
                self.timer_service.active_timers[self._timer_id]["end_time"] = (
                    time.time() + (self._pause_remaining or 0)
                )
            self._paused = False
            self.pause_btn.config(text="⏸ Pause")

    def _add_five(self):
        active = self.timer_service.get_all_active()
        if active:
            tid = active[0]["id"]
            self.timer_service.active_timers[tid]["end_time"] += 300  # +5 min
            self.timer_service.active_timers[tid]["total_duration"] += 300

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

    # ------------------------------------------------------------------ #
    #  Completion screen                                                   #
    # ------------------------------------------------------------------ #

    def _handle_timer_complete_event(self, *args):
        """Bus event callback — schedule on the main thread."""
        self.parent.after(0, self._on_timer_complete)

    def _on_timer_complete(self):
        """Replace the live timer UI with a 'Session Complete' screen."""
        if self._completed:
            return
        self._completed = True
        self._running   = False

        # Hide the running controls
        for widget in self.parent.winfo_children():
            widget.pack_forget()

        BG = self.BG
        FG = self.FG
        GREEN = self.BREAK_COLOR

        # Completion banner
        tk.Label(self.parent, text="✅", font=("Segoe UI", 28),
                 bg=BG, fg=GREEN).pack(pady=(16, 2))
        tk.Label(self.parent, text="Session Complete!",
                 font=("Segoe UI", 14, "bold"),
                 bg=BG, fg=FG).pack()
        tk.Label(self.parent, text="Great work. Take a breather.",
                 font=("Segoe UI", 9),
                 bg=BG, fg="#90A4AE").pack(pady=(2, 12))

        btn_frame = tk.Frame(self.parent, bg=BG)
        btn_frame.pack()

        tk.Button(btn_frame, text="▶ Continue",
                  command=self._dismiss,
                  bg=GREEN, fg="#000000",
                  relief="flat", padx=10, pady=5,
                  font=("Segoe UI", 10, "bold")).grid(row=0, column=0, padx=6)

        tk.Button(btn_frame, text="■ Close",
                  command=self._dismiss,
                  bg=self.BTN_BG, fg=FG,
                  relief="flat", padx=10, pady=5,
                  font=("Segoe UI", 10)).grid(row=0, column=1, padx=6)

    def _dismiss(self):
        """Signal the monitor thread that the tab can be removed."""
        self.timer_service.focus_tab_dismissed = True
