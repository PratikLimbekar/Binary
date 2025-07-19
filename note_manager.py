import os
from datetime import datetime

notes_dir = r'C:\Users\iprat\OneDrive\Desktop\Binary Notes'

if not os.path.exists(notes_dir):
    os.makedirs(notes_dir)

def save_note(text: str) -> str:
    """Save note with timestamp to a file named by today's date."""
    today = datetime.now().strftime('%Y-%m-%d')
    timestamp = datetime.now().strftime('%H:%M')
    filename = os.path.join(notes_dir, f'{today}.txt')
    with open(filename, 'a', encoding='utf-8') as f:
        f.write(f'{timestamp} - {text.strip()} \n')
    
    return f"Note saved at {timestamp} in {today}.txt"