import sys
import time
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class ChangeHandler(FileSystemEventHandler):
    def __init__(self):
        self.process = None
        self.restart_app()

    def restart_app(self):
        if self.process:
            self.process.terminate()
            self.process.wait()
        print("\n--- Restarting App ---\n")
        self.process = subprocess.Popen([sys.executable, "app/main.py"])

    def on_modified(self, event):
        if event.src_path.endswith('.py') or event.src_path.endswith('.qss'):
            self.restart_app()

if __name__ == "__main__":
    path = "app"
    event_handler = ChangeHandler()
    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)
    observer.start()
    print("Watching for changes in 'app/' directory...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        if event_handler.process:
            event_handler.process.terminate()
    observer.join()
