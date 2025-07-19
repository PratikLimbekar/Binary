from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time
import os
from docsinput import load_directory_and_embed

class TxtFileChangeHandler(FileSystemEventHandler):
    def __init__(self, directory):
        self.directory = directory

    def on_modified(self, event):
        if event.src_path.endswith(".txt"):
            print(f"[MODIFIED] {event.src_path}")
            load_directory_and_embed(self.directory)

    def on_created(self, event):
        if event.src_path.endswith(".txt"):
            print(f"[CREATED] {event.src_path}")
            load_directory_and_embed(self.directory)

    def on_deleted(self, event):
        if event.src_path.endswith(".txt"):
            print(f"[DELETED] {event.src_path}")
            load_directory_and_embed(self.directory)

def watch_folder(path):
    print(f"[WATCHING] Folder: {path}")
    event_handler = TxtFileChangeHandler(path)
    observer = Observer()
    observer.schedule(event_handler, path, recursive=False)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
