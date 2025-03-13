import time
import threading

def keep_alive():
    while True:
        print("Keeping alive...")  # Replace this with your task
        time.sleep(30)

# Run in a separate thread
thread = threading.Thread(target=keep_alive, daemon=True)
thread.start()

# Main program continues running
while True:
    time.sleep(1)  # Keep the main script running
