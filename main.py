
from aiogram import Bot, Dispatcher, executor, types
import os
from keep_alive import keep_alive

import random
import requests
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
keep_alive()
# Bot token
#TOKEN = Bot(token=os.environ.get('token'))
#dp = Dispatcher(TOKEN)
TOKEN = '6685826015:AAFb-AYP5ksaAo_PT_4KDpUVDjX1D_3NDlw'

# File paths for IBANs
iban_file_path_uk = 'iban.txt'
iban_file_path_italy = 'iban2.txt'
iban_file_path_france = 'iban3.txt'

# Base URL for IBAN validation API
base_url = "https://ibanapi.com"

# Proxy configuration (optional)
proxies = {
    "http": "http://tcnppbwe-rotate:m27wwonyzdza@p.webshare.io:80/",
    "http": "http://onosguhu-rotate:bua33b6mplf1@p.webshare.io:80/",
    "https": "http://onosguhu-rotate:bua33b6mplf1@p.webshare.io:80/",
    "https": "http://tcnppbwe-rotate:m27wwonyzdza@p.webshare.io:80/"
}

# Function to retrieve a random IBAN from a file
def get_random_iban_from_file(file_path):
    try:
        with open(file_path, 'r') as file:
            ibans = file.readlines()
        random_iban = random.choice(ibans).strip()
        return f"Valid IBAN: {random_iban}"
    except FileNotFoundError:
        return 'IBAN file not found.'

# Function to validate IBAN using the external API
def validate_iban(iban):
    # URL to get the CSRF token
    token_url = f"{base_url}/iban-checker"
    validate_url = f"{base_url}/validate-iban/{iban}"

    # Create a session
    session = requests.Session()

    try:
        # Fetch CSRF token
        response = session.get(token_url, proxies=proxies)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx and 5xx)
    except requests.exceptions.RequestException as e:
        print(f"Error fetching CSRF token: {e}")
        return None

    # Extract the CSRF token using BeautifulSoup
    soup = BeautifulSoup(response.text, "html.parser")
    csrf_token_meta = soup.find("meta", {"name": "csrf-token"})
    if not csrf_token_meta:
        print("CSRF token not found in the response. Aborting.")
        return None
    csrf_token = csrf_token_meta["content"]

    # Headers for the POST request
    headers = {
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "en-US,en;q=0.9",
        "Origin": base_url,
        "Referer": token_url,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "X-CSRF-TOKEN": csrf_token,
        "X-Requested-With": "XMLHttpRequest"
    }

    try:
        # Make the POST request to validate the IBAN
        response = session.post(validate_url, headers=headers, proxies=proxies)
        response.raise_for_status()  # Raise HTTPError for bad responses
    except requests.exceptions.RequestException as e:
        print(f"Error validating IBAN: {e}")
        return None

    # Parse JSON response
    try:
        data = response.json()
    except ValueError:
        print("Failed to parse JSON response. Check API response format.")
        return None

    # Process the response
    if data.get("result") == 200:
        bank_account = data["data"].get("bank_account")
        if bank_account:
            result = {
                "status": "success",
                "iban": iban,  # Include IBAN in the response
                "message": data.get("message"),
                "bank_account": bank_account,
                "country_code": data["data"].get("country_code", "N/A"),
                "country_name": data["data"].get("country_name", "N/A"),
                "currency_code": data["data"].get("currency_code", "N/A"),
                "bank_name": data["data"].get("bank", {}).get("bank_name", "N/A"),
                "bic": data["data"].get("bank", {}).get("bic", "N/A")
            }
        else:
            result = {"status": "failure", "iban": iban, "message": "IBAN is invalid."}
    else:
        result = {"status": "failure", "iban": iban, "message": data.get("message", "Unknown error occurred.")}

    return result

# Start command handler
async def start(update: Update, context: CallbackContext):
    username = update.message.from_user.username
    chat_id = update.message.chat.id
    message = f"Welcome to IBAN Generator and Validator!\nUsername: @{username}\nUser ID: {chat_id}\n\nGet IBAN or validate with commands:\n/getiban"
    await update.message.reply_text(message)

# /getiban command handler
async def get_iban_options(update: Update, context: CallbackContext):
    message = """
    GB & UK IBAN : /ibanDE
    ITALY IBAN : /ibanFR
    FRANCE IBAN: /ibanIT
    Validate IBAN with: .chk <iban>
    """
    await update.message.reply_text(message)

# /ibanDE command handler
async def get_iban_uk(update: Update, context: CallbackContext):
    iban = get_random_iban_from_file(iban_file_path_uk)
    await update.message.reply_text(iban)

# /ibanFR command handler
async def get_iban_italy(update: Update, context: CallbackContext):
    iban = get_random_iban_from_file(iban_file_path_italy)
    await update.message.reply_text(iban)

# /ibanIT command handler
async def get_iban_france(update: Update, context: CallbackContext):
    iban = get_random_iban_from_file(iban_file_path_france)
    await update.message.reply_text(iban)

# IBAN validation handler
async def check_iban(update: Update, context: CallbackContext):
    message_text = update.message.text.strip()

    # Check if the message starts with ".chk" and has an IBAN following it
    if message_text.lower().startswith(".chk "):
        iban = message_text[5:].strip()  # Remove the ".chk " part and get the IBAN
        result = validate_iban(iban)

        if result:
            if result["status"] == "success":
                response_message = (
                    f"IBAN Validation Successful! ✅\n"
                    f"IBAN: {result['iban']}\n"
                    f"Message: {result['message']}\n"
                    f"Bank Account: {result['bank_account']}\n"
                    f"Country Code: {result['country_code']}\n"
                    f"Country Name: {result['country_name']}\n"
                    f"Currency Code: {result['currency_code']}\n"
                    f"Bank Name: {result['bank_name']}\n"
                    f"BIC: {result['bic']}"
                )
            else:
                response_message = f"❌ {result['iban']} - {result['message']}"
            await update.message.reply_text(response_message)
    else:
        await update.message.reply_text("Please use the `.chk` prefix followed by an IBAN (e.g., `.chk GB29NWBK60161331926819`).")

# Main function to start the bot
def main():
    application = Application.builder().token(TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("getiban", get_iban_options))
    application.add_handler(CommandHandler("ibanDE", get_iban_uk))
    application.add_handler(CommandHandler("ibanFR", get_iban_italy))
    application.add_handler(CommandHandler("ibanIT", get_iban_france))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_iban))

    # Start the bot
    application.run_polling()

if __name__ == '__main__':
    main()
