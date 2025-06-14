import subprocess
import os
import sys
from dotenv import load_dotenv

def main():
    """
    Synchronizes the local test database with production data by running
    the sync_db.py script.
    """
    print("--- Running database setup and synchronization ---")
    
    # Assumes .env file is in the same directory as this script.
    dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path=dotenv_path)
    else:
        print("Warning: .env file not found. Proceeding with existing environment variables.")

    # Path to the synchronization script
    sync_script_path = os.path.join(os.path.dirname(__file__), "scripts", "sync_db.py")

    if not os.path.exists(sync_script_path):
        print(f"Error: Database sync script not found at {sync_script_path}")
        sys.exit(1)

    # We use the same python interpreter that's running this script
    python_executable = sys.executable
    result = subprocess.run([python_executable, sync_script_path], capture_output=True, text=True)

    if result.returncode != 0:
        print("--- DB Sync FAILED ---")
        print("--- STDOUT ---")
        print(result.stdout)
        print("--- STDERR ---")
        print(result.stderr)
        print("Database synchronization script failed.")
        sys.exit(1)
    
    print(result.stdout)
    print("--- Database setup complete. ---")

if __name__ == "__main__":
    main() 