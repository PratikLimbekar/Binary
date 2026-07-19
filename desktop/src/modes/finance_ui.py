import tkinter as tk
from tkinter import ttk

class FinanceUI:
    def __init__(self, parent, finance_service):
        self.parent = parent
        self.finance_service = finance_service
        self.setup_ui()

    def setup_ui(self):
        for widget in self.parent.winfo_children():
            widget.destroy()
            
        self.main_frame = tk.Frame(self.parent, bg="#36454F")
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Header with Close button
        header = tk.Frame(self.main_frame, bg="#36454F")
        header.pack(fill="x")
        
        title = tk.Label(header, text="PERSONAL FINANCE", font=("Segoe UI", 10, "bold"), bg="#36454F", fg="#4CAF50")
        title.pack(side="left", pady=5)
        
        close_btn = tk.Button(header, text="✕", command=self._close, bg="#36454F", fg="white", relief="flat")
        close_btn.pack(side="right")

        # Summary Cards
        summary = self.finance_service.get_summary()
        
        self.stats_frame = tk.Frame(self.main_frame, bg="#36454F")
        self.stats_frame.pack(fill="x", pady=10)

        self.create_stat_card(self.stats_frame, "Expense", f"₹{summary.get('monthly_expense', 0)}", "#FF5252")
        self.create_stat_card(self.stats_frame, "Income", f"₹{summary.get('monthly_income', 0)}", "#4CAF50")

        # Recent Transactions
        tk.Label(self.main_frame, text="RECENT LOGS", font=("Segoe UI", 8, "bold"), bg="#36454F", fg="white").pack(anchor="w")
        
        self.log_container = tk.Canvas(self.main_frame, bg="#353935", highlightthickness=0)
        self.log_container.pack(fill="both", expand=True, pady=5)
        
        self.log_frame = tk.Frame(self.log_container, bg="#353935")
        self.log_container.create_window((0,0), window=self.log_frame, anchor="nw")

        recent = summary.get('recent', [])
        import math
        for entry in reversed(recent):
            row = tk.Frame(self.log_frame, bg="#353935")
            row.pack(fill="x", pady=2)
            
            text = f"{entry['Description']} - ₹{entry['Amount']}"
            color = "#FFCDD2" if entry['Type'] == 'Expense' else "#C8E6C9"
            tk.Label(row, text=text, bg="#353935", fg=color, font=("Segoe UI", 9)).pack(side="left", padx=5)
            
            # Category Correction
            cat = str(entry.get('Category', 'nan')).lower()
            if cat == 'nan' or cat == 'none' or not cat:
                fix_btn = tk.Button(row, text="+ Add Category", font=("Segoe UI", 7), 
                                    bg="#2C3840", fg="#4CAF50", relief="flat",
                                    command=lambda e=entry: self._fix_category(e))
                fix_btn.pack(side="right", padx=5)
            else:
                tk.Label(row, text=f"({cat})", bg="#353935", fg="#90A4AE", font=("Segoe UI", 8)).pack(side="right", padx=5)

    def _fix_category(self, entry):
        # Quick popup or inline entry? Let's do a simple popup for now
        popup = tk.Toplevel(self.parent)
        popup.title("Fix Category")
        popup.geometry("200x100")
        popup.config(bg="#36454F")
        popup.attributes("-topmost", True)
        
        tk.Label(popup, text=f"Category for {entry['Description']}:", bg="#36454F", fg="white", font=("Segoe UI", 8)).pack(pady=5)
        ent = tk.Entry(popup)
        ent.pack(pady=5)
        ent.focus_set()
        
        def save():
            new_cat = ent.get().strip()
            if new_cat:
                # Update in CSV
                import pandas as pd
                df = pd.read_csv(self.finance_service.data_path)
                # Find matching row by timestamp
                df.loc[df['Timestamp'] == entry['Timestamp'], 'Category'] = new_cat
                df.to_csv(self.finance_service.data_path, index=False)
                popup.destroy()
                # Refresh UI
                for widget in self.main_frame.winfo_children():
                    widget.destroy()
                self.setup_ui()

        tk.Button(popup, text="Save", command=save, bg="#4CAF50").pack()

    def _close(self):
        from src.core.event_bus import bus
        bus.publish("ui.remove_tab", "Finance")

    def create_stat_card(self, parent, label, value, color):
        card = tk.Frame(parent, bg="#353935", highlightbackground=color, highlightthickness=1)
        card.pack(side="left", fill="both", expand=True, padx=5)
        tk.Label(card, text=label, font=("Segoe UI", 8), bg="#353935", fg="white").pack()
        tk.Label(card, text=value, font=("Segoe UI", 12, "bold"), bg="#353935", fg=color).pack()

# Global instance not needed
