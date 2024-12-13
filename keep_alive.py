from flask import Flask
from threading import Thread
import requests
import time
import logging

app = Flask(__name__)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

@app.route('/')
def index():
    return "Alive"

def run():
    app.run(host='0.0.0.0', port=8080)

def check_website(url, check_interval=40):
    while True:
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                logging.info(f"Website {url} is reachable.")
            else:
                logging.warning(f"Website {url} returned status code: {response.status_code}")
        except requests.exceptions.RequestException as e:
            logging.error(f"Error checking website {url}: {e}")
        time.sleep(check_interval)


def keep_alive(url, check_interval=40):
    flask_thread = Thread(target=run, daemon=True)
    flask_thread.start()

    checker_thread = Thread(target=check_website, args=(url, check_interval), daemon=True)
    checker_thread.start()



if __name__ == "__main__":
    website_url = "https://iban.onrender.com"  # Replace with the URL you want to check
    keep_alive(website_url)

    while True:
        time.sleep(60)  # Keep the main thread alive (can be adjusted)
