import tkinter as tk

# Styling Constants matching main_window
COLOR_BUTTON = "#36454F"
COLOR_FG = "#FEFCFB"
COLOR_ROOT = "#353935"
COLOR_ACTIVE = "#151b1f"
COLOR_HOVER = "#2c3840"

class ScrollableNotebook(tk.Frame):
    def __init__(self, parent, *args, **kwargs):
        # Remove any ttk.Notebook specific arguments if they leak in
        kwargs.pop("style", None)
        super().__init__(parent, bg=COLOR_BUTTON, *args, **kwargs)
        
        self.tabs = {}  # child_frame -> {"text": str, "button": tk.Button}
        self.active_tab = None
        
        # Grid layout for self:
        # Row 0: Tab header frame (containing left scroll button, canvas, right scroll button)
        # Row 1: Content container frame (expanding)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # Header Frame
        self.header_frame = tk.Frame(self, bg=COLOR_BUTTON)
        self.header_frame.grid(row=0, column=0, sticky="ew")
        
        # Scroll Buttons (hidden initially, only packed if tabs exceed width)
        self.left_btn = tk.Button(
            self.header_frame, text="◀", command=self._scroll_left,
            bg=COLOR_BUTTON, fg=COLOR_FG, relief="flat", bd=0,
            activebackground=COLOR_BUTTON, activeforeground=COLOR_FG,
            font=("Segoe UI", 7, "bold"), padx=5, cursor="hand2"
        )
        self.right_btn = tk.Button(
            self.header_frame, text="▶", command=self._scroll_right,
            bg=COLOR_BUTTON, fg=COLOR_FG, relief="flat", bd=0,
            activebackground=COLOR_BUTTON, activeforeground=COLOR_FG,
            font=("Segoe UI", 7, "bold"), padx=5, cursor="hand2"
        )
        
        # Canvas for tabs scrolling
        self.canvas = tk.Canvas(self.header_frame, bg=COLOR_BUTTON, width=1, height=28, highlightthickness=0, bd=0)
        self.canvas.pack(side="left", fill="x", expand=True)
        
        # Inner Frame inside canvas holding the actual tab buttons
        self.tabs_container = tk.Frame(self.canvas, bg=COLOR_BUTTON)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.tabs_container, anchor="nw")
        
        # Event bindings for resize/scroll region updates
        self.tabs_container.bind("<Configure>", self._on_container_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        
        # Bind MouseWheel to scroll tabs only when mouse hover is over tab header canvas
        self.canvas.bind("<Enter>", lambda e: self.canvas.bind_all("<MouseWheel>", self._on_mousewheel))
        self.canvas.bind("<Leave>", lambda e: self.canvas.unbind_all("<MouseWheel>"))
        
        # Content container where active tab frames are placed
        self.content_container = tk.Frame(self, bg=COLOR_BUTTON)
        self.content_container.grid(row=1, column=0, sticky="nsew")

    # ── Scroll Region & Resize Handling ───────────────────────────────────────
    def _on_container_configure(self, event=None):
        """Update scroll region of canvas when contents resize."""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self._update_scroll_buttons()

    def _on_canvas_configure(self, event):
        """Make sure the inner container frame matches canvas height, and check scroll buttons."""
        self.canvas.itemconfigure(self.canvas_window, height=event.height)
        self._update_scroll_buttons()

    def _update_scroll_buttons(self):
        """Packs scroll navigation arrows if tabs container width exceeds canvas width."""
        self.update_idletasks()
        req_width = self.tabs_container.winfo_reqwidth()
        canvas_width = self.canvas.winfo_width()
        
        # Only show navigation buttons if the tab buttons overflow the canvas width
        if req_width > canvas_width and canvas_width > 1:
            if not self.left_btn.winfo_ismapped():
                # Re-pack correctly to place canvas between left and right arrows
                self.canvas.pack_forget()
                self.left_btn.pack(side="left", fill="y")
                self.canvas.pack(side="left", fill="x", expand=True)
                self.right_btn.pack(side="right", fill="y")
        else:
            if self.left_btn.winfo_ismapped():
                self.left_btn.pack_forget()
                self.right_btn.pack_forget()

    # ── Scroll Methods ────────────────────────────────────────────────────────
    def _scroll_left(self):
        self.canvas.xview_scroll(-1, "units")

    def _scroll_right(self):
        self.canvas.xview_scroll(1, "units")

    def _on_mousewheel(self, event):
        if event.delta:
            # On Windows: event.delta is typically multiples of 120
            self.canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")

    def _scroll_to_button(self, button):
        """Ensures that the selected tab button is visible within the canvas view."""
        self.update_idletasks()
        btn_x = button.winfo_x()
        btn_width = button.winfo_width()
        canvas_width = self.canvas.winfo_width()
        container_width = self.tabs_container.winfo_width()
        
        if container_width <= 0:
            return
            
        scroll_left, scroll_right = self.canvas.xview()
        left_pixel = scroll_left * container_width
        right_pixel = scroll_right * container_width
        
        if btn_x < left_pixel:
            # Scroll left so the button aligns with the left edge of the visible canvas
            self.canvas.xview_moveto(btn_x / container_width)
        elif (btn_x + btn_width) > right_pixel:
            # Scroll right so the button aligns with the right edge of the visible canvas
            self.canvas.xview_moveto((btn_x + btn_width - canvas_width) / container_width)

    # ── ttk.Notebook Compatibility API ─────────────────────────────────────────
    def add(self, child, text=""):
        """Add a new child frame to the notebook."""
        if child in self.tabs:
            return
        
        # Create a beautiful, flat tab button with hover styling
        btn = tk.Button(
            self.tabs_container, text=text, bg=COLOR_BUTTON, fg=COLOR_FG,
            relief="flat", bd=0, font=("Segoe UI", 9), padx=12, pady=5,
            activebackground=COLOR_BUTTON, activeforeground=COLOR_FG, cursor="hand2"
        )
        btn.configure(command=lambda c=child: self.select(c))
        
        # Hover effect bindings
        btn.bind("<Enter>", lambda e, b=btn, c=child: b.configure(bg=COLOR_HOVER) if self.active_tab != c else None)
        btn.bind("<Leave>", lambda e, b=btn, c=child: b.configure(bg=COLOR_BUTTON) if self.active_tab != c else None)
        
        btn.pack(side="left", fill="y")
        
        self.tabs[child] = {"text": text, "button": btn}
        
        # Hide child initially
        child.pack_forget()
        
        # If it's the first tab added, select it
        if len(self.tabs) == 1:
            self.select(child)
            
        self._on_container_configure()

    def forget(self, child):
        """Remove a child frame from the notebook."""
        if child not in self.tabs:
            return
        
        # Destroy tab button and hide frame
        btn = self.tabs[child]["button"]
        btn.destroy()
        child.pack_forget()
        
        del self.tabs[child]
        
        # If the closed tab was active, switch active tab to first remaining
        if self.active_tab == child:
            self.active_tab = None
            if self.tabs:
                first_remaining = list(self.tabs.keys())[0]
                self.select(first_remaining)
                
        self._on_container_configure()

    def select(self, child=None):
        """Gets the active frame or sets the active frame."""
        if child is None:
            return self.active_tab
            
        if child not in self.tabs:
            return
            
        # De-activate current active tab
        if self.active_tab and self.active_tab in self.tabs:
            self.active_tab.pack_forget()
            self.tabs[self.active_tab]["button"].configure(bg=COLOR_BUTTON, font=("Segoe UI", 9))
            
        self.active_tab = child
        
        # Activate and pack new active tab
        child.pack(in_=self.content_container, fill="both", expand=True)
        self.tabs[child]["button"].configure(bg=COLOR_ACTIVE, font=("Segoe UI", 9, "bold"))
        
        # Auto-scroll selected button into view
        self._scroll_to_button(self.tabs[child]["button"])
        
        # Let the window recalculate its optimal size for this tab's content
        self.after(1, lambda: self.winfo_toplevel().geometry(""))

    def tab(self, child, option):
        """Gets a configuration option of a tab (e.g. 'text')."""
        if child not in self.tabs:
            return ""
        if option == "text":
            return self.tabs[child]["text"]
        return ""
