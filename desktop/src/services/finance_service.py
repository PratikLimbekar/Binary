import os
import pandas as pd
from datetime import datetime
from src.core.event_bus import bus

_BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

class FinanceService:
    def __init__(self, data_path=None):
        self.data_path = data_path or os.path.join(_BASE_DIR, 'data', 'finance.csv')
        os.makedirs(os.path.dirname(self.data_path), exist_ok=True)
        if not os.path.exists(self.data_path):
            df = pd.DataFrame(columns=["Timestamp", "Amount", "Category", "Description", "Type"])
            df.to_csv(self.data_path, index=False)

    def log_transaction(self, amount, category, description, trans_type="Expense"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_row = {
            "Timestamp": timestamp,
            "Amount": amount,
            "Category": category,
            "Description": description,
            "Type": trans_type
        }
        df = pd.read_csv(self.data_path)
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        df.to_csv(self.data_path, index=False)
        
        from src.modes.finance_ui import FinanceUI
        bus.publish("ui.add_tab", "Finance", lambda p: FinanceUI(p, self))
        
        return f"Logged {trans_type}: {amount} for {description} ({category})."

    def get_summary(self):
        df = pd.read_csv(self.data_path)
        if df.empty:
            return "No transactions logged yet."
        
        # Simple monthly summary
        df['Timestamp'] = pd.to_datetime(df['Timestamp'])
        current_month = datetime.now().month
        current_year = datetime.now().year
        
        monthly_df = df[(df['Timestamp'].dt.month == current_month) & (df['Timestamp'].dt.year == current_year)]
        
        total_expense = monthly_df[monthly_df['Type'] == 'Expense']['Amount'].sum()
        total_income = monthly_df[monthly_df['Type'] == 'Income']['Amount'].sum()
        
        return {
            "monthly_expense": total_expense,
            "monthly_income": total_income,
            "recent": df.tail(5).to_dict('records')
        }

# Global instance
finance_service = FinanceService()
