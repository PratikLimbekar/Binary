import tkinter as tk
from tkinter import ttk

class FinanceUI:
    def __init__(self, parent, finance_service):
        self.parent = parent
        self.finance_service = finance_service
        self.setup_ui()

    def setup_ui(self):
        self.main_frame = tk.Frame(self.parent, bg="#36454F")
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        title = tk.Label(self.main_frame, text="PERSONAL FINANCE", font=("Segoe UI", 10, "bold"), bg="#36454F", fg="#4CAF50")
        title.pack(pady=5)

        # Summary Cards
        summary = self.finance_service.get_summary()
        
        self.stats_frame = tk.Frame(self.main_frame, bg="#36454F")
        self.stats_frame.pack(fill="x", pady=10)

        self.create_stat_card(self.stats_frame, "Expense", f"₹{summary.get('monthly_expense', 0)}", "#FF5252")
        self.create_stat_card(self.stats_frame, "Income", f"₹{summary.get('monthly_income', 0)}", "#4CAF50")

        # Recent Transactions
        tk.Label(self.main_frame, text="RECENT LOGS", font=("Segoe UI", 8, "bold"), bg="#36454F", fg="white").pack(anchor="w")
        
        self.log_frame = tk.Frame(self.main_frame, bg="#353935")
        self.log_frame.pack(fill="both", expand=True, pady=5)

        recent = summary.get('recent', [])
        for entry in reversed(recent):
            text = f"{entry['Description']} - ₹{entry['Amount']}"
            color = "#FFCDD2" if entry['Type'] == 'Expense' else "#C8E6C9"
            tk.Label(self.log_frame, text=text, bg="#353935", fg=color, font=("Segoe UI", 9)).pack(anchor="w", padx=5)

    def create_stat_card(self, parent, label, value, color):
        card = tk.Frame(parent, bg="#353935", highlightbackground=color, highlightthickness=1)
        card.pack(side="left", fill="both", expand=True, padx=5)
        tk.Label(card, text=label, font=("Segoe UI", 8), bg="#353935", fg="white").pack()
        tk.Label(card, text=value, font=("Segoe UI", 12, "bold"), bg="#353935", fg=color).pack()

# Global instance not needed
