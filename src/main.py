import sys
import os
import psutil
from dotenv import load_dotenv

# Workaround for protobuf compatibility issue
# Fixes: TypeError: Descriptors cannot be created directly.
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

# Add src to python path to handle modular imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

def setup_environment():
    """Load environment variables and ensure logs directory exists."""
    # Load .env from project root
    env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    load_dotenv(dotenv_path=env_path)
    
    # Ensure logs directory exists
    logs_dir = os.path.join(os.path.dirname(__file__), '..', 'logs')
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)

def optimize_process():
    """Sets the process priority to Below Normal to ensure system stability."""
    try:
        p = psutil.Process(os.getpid())
        # On Windows, this is BELOW_NORMAL_PRIORITY_CLASS
        if os.name == 'nt':
            p.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
        else:
            p.nice(10) # POSIX nice value
        print("Optimization: Process priority set to Below Normal.")
    except Exception as e:
        print(f"Optimization failed: {e}")

def main():
    print("Initializing Binary AI Assistant...")
    setup_environment()
    optimize_process()
    
    # Import GUI here to ensure environment is set up first
    from src.gui.main_window import root, start_app
    
    print("Launching Interface...")
    start_app()
    root.mainloop()

if __name__ == "__main__":
    main()
