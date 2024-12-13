from flask import Flask, render_template
from threading import Thread
import requests
import time

app = Flask(__name__)

@app.route('/')
def index():
    return "Alive"

def run():
    app.run(host='0.0.0.0', port=8080)

def ping_website():
    while True:
        try:
            response = requests.get('https://iban.onrender.com/')  # Replace with your deployed URL if needed
            print(f"Pinged website, status code: {response.status_code}")
            return response
        except Exception as e:
            print(f"Error pinging website: {e}")
        time.sleep(1800)  # Wait for 30 minutes (1800 seconds)

def keep_alive():
    t1 = Thread(target=run)
    t2 = Thread(target=ping_website)
    t1.start()
    t2.start()
