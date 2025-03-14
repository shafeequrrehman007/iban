from flask import Flask
import threading
import time

app = Flask(__name__)

@app.route('/')
def home():
    return "Server is running!"

def keep_alive():
    while True:
        print("Keeping alive...")
        time.sleep(30)

# Start keep-alive thread
thread = threading.Thread(target=keep_alive, daemon=True)
thread.start()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
