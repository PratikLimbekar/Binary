import tkinter as tk
from tkinter import messagebox
from src.services.sticky_note_service import sticky_note_service

COLOR_BUTTON = "#36454F"
COLOR_FG = "#FEFCFB"
COLOR_ROOT = "#353935"

class StickyNotesUI(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=COLOR_BUTTON)
        self.parent = parent
        self.active_note = None
        self.is_list_view = False
        
        # Load settings
        self.width = sticky_note_service.get_workspace_width()
        
        self.setup_ui()
        self.load_active_note()

        # Bind destroy event to save state
        self.bind("<Destroy>", self.on_destroy)

    def setup_ui(self):
        # Configure layout
        # Row 0: Top Toolbar (Notes List, Close Buttons)
        # Row 1: Workspace + Drag Handle
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # ── Toolbar ───────────────────────────────────────────────────────────
        self.toolbar = tk.Frame(self, bg=COLOR_BUTTON)
        self.toolbar.grid(row=0, column=0, columnspan=2, padx=10, pady=(5, 5), sticky="ew")

        # Notes list button (Custom Icon) - unicode '▤' (Document list symbol)
        self.list_btn = tk.Button(
            self.toolbar, text="▤ Notes", command=self.toggle_view,
            bg=COLOR_BUTTON, fg=COLOR_FG, relief="flat", bd=0,
            activebackground="#2c3840", activeforeground=COLOR_FG,
            font=("Segoe UI", 9, "bold"), padx=8, pady=3, cursor="hand2"
        )
        self.list_btn.pack(side="left")

        # Close button (Unicode '✕' - multiplication sign, clean and not emoji)
        self.close_btn = tk.Button(
            self.toolbar, text="✕", command=self.close_tab,
            bg=COLOR_BUTTON, fg=COLOR_FG, relief="flat", bd=0,
            activebackground="#ff5252", activeforeground=COLOR_FG,
            font=("Segoe UI", 10, "bold"), padx=8, pady=3, cursor="hand2"
        )
        self.close_btn.pack(side="right")

        # ── Main Container (Holds Workspace & Resize Handle) ──────────────────
        self.main_container = tk.Frame(self, bg=COLOR_BUTTON)
        self.main_container.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=10, pady=(0, 10))
        self.main_container.grid_rowconfigure(0, weight=1)

        # ── Sticky Note Workspace (Draggable Width) ───────────────────────────
        self.workspace = tk.Frame(self.main_container, bg=COLOR_BUTTON, width=self.width)
        self.workspace.grid(row=0, column=0, sticky="ns")
        self.workspace.grid_propagate(False)  # Prevent grid from overriding explicit width

        # ── Resize Handle (Thin bar on the right side) ────────────────────────
        self.resize_handle = tk.Frame(self.main_container, bg=COLOR_BUTTON, width=5, cursor="size_we")
        self.resize_handle.grid(row=0, column=1, sticky="ns")

        # Bind hover effects and drag events for resize handle
        self.resize_handle.bind("<Enter>", lambda e: self.resize_handle.configure(bg="#7692ff"))
        self.resize_handle.bind("<Leave>", lambda e: self.resize_handle.configure(bg=COLOR_BUTTON))
        self.resize_handle.bind("<Button-1>", self.start_resize)
        self.resize_handle.bind("<B1-Motion>", self.perform_resize)
        self.resize_handle.bind("<ButtonRelease-1>", self.end_resize)

        # ── Editor View Frame ─────────────────────────────────────────────────
        self.editor_frame = tk.Frame(self.workspace, bg="#FFF59D") # Pastel yellow body
        
        # Title Segment wrapper (provides inset padding)
        self.title_container = tk.Frame(self.editor_frame, bg="#FFE082") # Slightly darker pastel yellow
        self.title_container.pack(fill="x", ipady=2)

        self.title_entry = tk.Entry(
            self.title_container, bg="#FFE082", fg="#212121",
            insertbackground="#212121", relief="flat", bd=0,
            font=("Segoe UI", 11, "bold"), highlightthickness=0
        )
        self.title_entry.pack(fill="x", padx=10, pady=5)
        self.title_entry.bind("<KeyRelease>", self.on_content_changed)

        # Divider line
        self.divider = tk.Frame(self.editor_frame, bg="#E0D580", height=1)
        self.divider.pack(fill="x")

        # Text Area Segment
        self.text_area = tk.Text(
            self.editor_frame, bg="#FFF59D", fg="#212121",
            insertbackground="#212121", relief="flat", bd=0,
            font=("Segoe UI", 10), wrap="word", highlightthickness=0,
            padx=10, pady=10
        )
        self.text_area.pack(fill="both", expand=True)
        self.text_area.bind("<KeyRelease>", self.on_content_changed)

        # ── List View Frame ───────────────────────────────────────────────────
        self.list_frame = tk.Frame(self.workspace, bg="#2C3840") # Cozy dark list background
        
        # List Header
        self.list_header = tk.Frame(self.list_frame, bg="#36454F")
        self.list_header.pack(fill="x")
        
        tk.Label(
            self.list_header, text="Sticky Notes", bg="#36454F", fg=COLOR_FG,
            font=("Segoe UI", 10, "bold")
        ).pack(side="left", padx=10, pady=8)

        # "+ New" Button inside List View
        self.new_note_btn = tk.Button(
            self.list_header, text="+ New", command=self.create_new_note,
            bg="#7692ff", fg="white", font=("Segoe UI", 8, "bold"),
            relief="flat", bd=0, activebackground="#5d78e5", activeforeground="white",
            padx=6, pady=2, cursor="hand2"
        )
        self.new_note_btn.pack(side="right", padx=10, pady=8)

        # Scrollable list container
        self.list_scroll_canvas = tk.Canvas(self.list_frame, bg="#2C3840", highlightthickness=0, bd=0)
        self.list_scroll_scrollbar = tk.Scrollbar(self.list_frame, orient="vertical", command=self.list_scroll_canvas.yview)
        
        self.list_items_container = tk.Frame(self.list_scroll_canvas, bg="#2C3840")
        self.list_scroll_window = self.list_scroll_canvas.create_window((0, 0), window=self.list_items_container, anchor="nw")
        
        self.list_items_container.bind("<Configure>", lambda e: self.list_scroll_canvas.configure(scrollregion=self.list_scroll_canvas.bbox("all")))
        self.list_scroll_canvas.bind("<Configure>", lambda e: self.list_scroll_canvas.itemconfigure(self.list_scroll_window, width=e.width))
        
        self.list_scroll_canvas.configure(yscrollcommand=self.list_scroll_scrollbar.set)
        
        self.list_scroll_scrollbar.pack(side="right", fill="y")
        self.list_scroll_canvas.pack(side="left", fill="both", expand=True)

        # Default: show editor frame
        self.editor_frame.pack(fill="both", expand=True)

    # ── Resize Logic ──────────────────────────────────────────────────────────
    def start_resize(self, event):
        self.start_x = event.x_root
        self.start_width = self.workspace.winfo_width()

    def perform_resize(self, event):
        dx = event.x_root - self.start_x
        new_width = self.start_width + dx
        # Clamp width between 200px and 600px
        new_width = max(200, min(600, new_width))
        
        self.width = new_width
        self.workspace.configure(width=new_width)
        # Update settings in real-time
        sticky_note_service.set_workspace_width(new_width)

    def end_resize(self, event):
        # Force redraw and save settings
        self.update_idletasks()
        sticky_note_service.save_state()

    # ── Notes Management & Loading ────────────────────────────────────────────
    def load_active_note(self):
        """Loads the current active note into the Editor."""
        self.active_note = sticky_note_service.get_active_note()
        
        self.title_entry.delete(0, tk.END)
        self.title_entry.insert(0, self.active_note.get("title", "New Note"))
        
        self.text_area.delete("1.0", tk.END)
        self.text_area.insert("1.0", self.active_note.get("content", ""))

    def save_current_note(self):
        """Saves current Editor fields back to active note in database."""
        if not self.active_note:
            return
        
        title = self.title_entry.get()
        content = self.text_area.get("1.0", tk.END).rstrip("\n")
        
        sticky_note_service.save_note(self.active_note["id"], title, content)

    def on_content_changed(self, event=None):
        """Autosave on typing (KeyRelease)."""
        self.save_current_note()

    def create_new_note(self):
        """Creates a new empty note and loads it."""
        self.save_current_note() # Save current note first
        self.active_note = sticky_note_service.create_new_note("New Note", "")
        self.load_active_note()
        
        # If in list view, go back to editor view to show it
        if self.is_list_view:
            self.toggle_view()

    def delete_note_action(self, note_id, event=None):
        """Deletes a note and refreshes list."""
        if len(sticky_note_service.notes) <= 1:
            messagebox.showwarning("Sticky Notes", "You must keep at least one note.")
            return

        note = sticky_note_service.notes.get(note_id)
        title = note.get("title", "Untitled Note") if note else "this note"
        
        if messagebox.askyesno("Delete Note", f"Are you sure you want to delete '{title}'?"):
            sticky_note_service.delete_note(note_id)
            if self.active_note and self.active_note["id"] == note_id:
                self.load_active_note()
            self.populate_list_view()

    # ── View Switching & List View ────────────────────────────────────────────
    def toggle_view(self):
        """Toggles between note Editor and Notes List view."""
        self.save_current_note() # Save current note upon switching view
        
        if self.is_list_view:
            # Switch to Editor View
            self.list_frame.pack_forget()
            self.editor_frame.pack(fill="both", expand=True)
            self.list_btn.configure(text="▤ Notes", bg=COLOR_BUTTON)
            self.is_list_view = False
            self.load_active_note()
        else:
            # Switch to List View
            self.editor_frame.pack_forget()
            self.list_frame.pack(fill="both", expand=True)
            self.list_btn.configure(text="✎ Edit", bg="#151b1f")
            self.is_list_view = True
            self.populate_list_view()

    def populate_list_view(self):
        """Populates scrollable list of notes sorted by recency."""
        # Clear existing items
        for widget in self.list_items_container.winfo_children():
            widget.destroy()

        sorted_notes = sticky_note_service.get_all_notes_sorted()
        active_id = sticky_note_service.settings.get("active_note_id")

        for note in sorted_notes:
            nid = note["id"]
            title = note.get("title", "Untitled Note")
            
            # Highlight current active note in the list
            is_active = (nid == active_id)
            item_bg = "#36454F" if is_active else "#2C3840"
            border_color = "#7692ff" if is_active else "#2C3840"
            
            # Row frame for each item
            row_frame = tk.Frame(self.list_items_container, bg=item_bg, highlightbackground=border_color, highlightthickness=1)
            row_frame.pack(fill="x", padx=10, pady=5)
            
            # Note title button
            note_btn = tk.Button(
                row_frame, text=f"• {title}", bg=item_bg, fg=COLOR_FG,
                relief="flat", bd=0, activebackground="#36454F", activeforeground=COLOR_FG,
                font=("Segoe UI", 9, "bold" if is_active else "normal"), anchor="w",
                padx=8, pady=6, cursor="hand2",
                command=lambda n=nid: self.select_note_from_list(n)
            )
            note_btn.pack(side="left", fill="x", expand=True)

            # Delete button (unicode '✕' - clean list delete icon)
            del_btn = tk.Button(
                row_frame, text="✕", bg=item_bg, fg="#B0BEC5",
                relief="flat", bd=0, activebackground="#ff5252", activeforeground="white",
                font=("Segoe UI", 8), padx=6, cursor="hand2",
                command=lambda n=nid: self.delete_note_action(n)
            )
            del_btn.pack(side="right")
            
            # Double click also edits
            note_btn.bind("<Double-Button-1>", lambda e, n=nid: self.select_note_from_list(n))

    def select_note_from_list(self, note_id):
        """Selects a note from the list, saves state, and loads editor."""
        sticky_note_service.settings["active_note_id"] = note_id
        sticky_note_service.save_state()
        self.toggle_view() # Switches back to Editor View

    # ── Close & Destructor Hooks ──────────────────────────────────────────────
    def close_tab(self):
        """Closes the tab, saves everything, and removes it from UI."""
        self.save_current_note()
        sticky_note_service.set_tab_visible(False)
        
        from src.core.event_bus import bus
        bus.publish("ui.remove_tab", "Sticky Notes")

    def on_destroy(self, event=None):
        """Saves current state when widget is destroyed (e.g. app closing)."""
        # Make sure we only react to the destroy of the main widget itself
        if event and event.widget != self:
            return
        self.save_current_note()
        sticky_note_service.save_state()
