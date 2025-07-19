from docsinput import load_directory_and_embed
from watcher import watch_folder

aippdirectory = r'C:\Users\iprat\OneDrive\Desktop\AIPP'

# First-time embedding
load_directory_and_embed(aippdirectory)

# Start watching for future file changes
watch_folder(aippdirectory)
