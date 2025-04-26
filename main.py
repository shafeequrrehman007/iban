from aiogram import Bot, Dispatcher, executor, types
import os
import random
import requests
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
import keep_alive
import logging  # Import the logging module

# Bot token
TOKEN = '6685826015:AAFb-AYP5ksaAo_PT_4KDpUVDjX1D_3NDlw'  # Replace with your actual token

# File paths for IBANs
iban_file_path_uk = 'iban.txt'
iban_file_path_italy = 'iban2.txt'
iban_file_path_france = 'iban3.txt'

# File to store user IDs
user_file = 'users.txt'

# keep_alive.keep_alive()  # call keep_alive *before* instantiating the bot

# Base URL for IBAN validation API
base_url = "https://ibanapi.com"

# Proxy configuration (optional)
proxies = {
    "http": "http://tcnppbwe-rotate:m27wwonyzdza@p.webshare.io:80/",
    "http": "http://onosguhu-rotate:bua33b6mplf1@p.webshare.io:80/",
    "https": "http://onosguhu-rotate:bua33b6mplf1@p.webshare.io:80/",
    "https": "http://tcnppbwe-rotate:m27wwonyzdza@p.webshare.io:80/"
}

# Configure logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)


# Function to retrieve a random IBAN from a file
def get_random_iban_from_file(file_path):
    try:
        with open(file_path, 'r') as file:
            ibans = file.readlines()
        random_iban = random.choice(ibans).strip()
        return random_iban  # Return only the IBAN, not the "Valid IBAN: " prefix
    except FileNotFoundError:
        logger.warning(f"IBAN file not found: {file_path}") # Log warning
        return None  # Return None if file not found

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
        logger.error(f"Error fetching CSRF token: {e}") #Log error
        return None

    # Extract the CSRF token using BeautifulSoup
    soup = BeautifulSoup(response.text, "html.parser")
    csrf_token_meta = soup.find("meta", {"name": "csrf-token"})
    if not csrf_token_meta:
        logger.error("CSRF token not found in the response. Aborting.") #Log error
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
        logger.error(f"Error validating IBAN: {e}")  #Log error
        return None

    # Parse JSON response
    try:
        data = response.json()
    except ValueError:
        logger.error("Failed to parse JSON response. Check API response format.") #Log error
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

# Function to format the IBAN validation response
def format_validation_response(result):
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
    return response_message

# Function to save user ID
async def save_user(user_id):
    try:
        with open(user_file, 'a+') as f:
            f.seek(0)  # Rewind to the beginning of the file
            if str(user_id) + '\n' not in f.readlines():
                f.write(str(user_id) + '\n')
                logger.info(f"Saved new user ID: {user_id}") # Log info
                return True
            return False
    except Exception as e:
        logger.error(f"Error saving user ID {user_id}: {e}") # Log error
        return False

# Function to read user IDs from file
def get_user_ids():
    try:
        with open(user_file, 'r') as f:
            return [int(line.strip()) for line in f.readlines()]
    except FileNotFoundError:
        logger.warning("User file not found. No users loaded.") #Log warning
        return []
    except Exception as e:
        logger.error(f"Error reading user IDs: {e}") # Log error
        return []

# Function to broadcast a message
async def broadcast(context: CallbackContext, message: str):
    user_ids = get_user_ids()
    for user_id in user_ids:
        try:
            await context.bot.send_message(chat_id=user_id, text=message)
        except Exception as e:
            logger.error(f"Failed to send message to user {user_id}: {e}") # Log error

# Start command handler
async def start(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    username = update.message.from_user.username
    chat_id = update.message.chat.id
    message = f"Welcome to IBAN Generator and Validator!\nUsername: @{username}\nUser ID: {chat_id}\n\nGet IBAN and validate with commands:\n/ibanDE\n/ibanFR\n/ibanIT\n\nValidate IBAN with: .chk <iban>"
    await update.message.reply_text(message)

    # Save user ID
    if await save_user(user_id):
        logger.info(f"New user saved: {user_id}") # Log info

# /ibanDE command handler
async def get_and_validate_iban_uk(update: Update, context: CallbackContext):
    iban = get_random_iban_from_file(iban_file_path_uk)
    if iban:
        result = validate_iban(iban)
        if result:
            response_message = format_validation_response(result)
            await update.message.reply_text(response_message)
        else:
            await update.message.reply_text("Error validating IBAN from UK file.")
    else:
        await update.message.reply_text("Could not retrieve IBAN from UK file.")

# /ibanFR command handler
async def get_and_validate_iban_italy(update: Update, context: CallbackContext):
    iban = get_random_iban_from_file(iban_file_path_italy)
    if iban:
        result = validate_iban(iban)
        if result:
            response_message = format_validation_response(result)
            await update.message.reply_text(response_message)
        else:
            await update.message.reply_text("Error validating IBAN from Italy file.")
    else:
        await update.message.reply_text("Could not retrieve IBAN from Italy file.")

# /ibanIT command handler
async def get_and_validate_iban_france(update: Update, context: CallbackContext):
    iban = get_random_iban_from_file(iban_file_path_france)
    if iban:
        result = validate_iban(iban)
        if result:
            response_message = format_validation_response(result)
            await update.message.reply_text(response_message)
        else:
            await update.message.reply_text("Error validating IBAN from France file.")
    else:
        await update.message.reply_text("Could not retrieve IBAN from France file.")

# IBAN validation handler
async def check_iban(update: Update, context: CallbackContext):
    message_text = update.message.text.strip()

    # Check if the message starts with ".chk" and has an IBAN following it
    if message_text.lower().startswith(".chk "):
        iban = message_text[5:].strip()  # Remove the ".chk " part and get the IBAN
        result = validate_iban(iban)

        if result:
            response_message = format_validation_response(result)
            await update.message.reply_text(response_message)
        else:
            await update.message.reply_text("Error validating IBAN.")
    else:
        await update.message.reply_text("Please use the `.chk` prefix followed by an IBAN (e.g., `.chk GB29NWBK60161331926819`).")

# /broadcast command handler (ADMIN ONLY)
async def broadcast_command(update: Update, context: CallbackContext):
    # Replace YOUR_ADMIN_USER_ID with the actual admin user ID
    ADMIN_USER_ID = 123456789  # Example.  Important to change it.
    if update.message.from_user.id == ADMIN_USER_ID:
        message = ' '.join(context.args)  # Get the broadcast message from the command arguments
        if message:
            await broadcast(context, message)
            await update.message.reply_text("Broadcast message sent!")
        else:
            await update.message.reply_text("Please provide a message to broadcast.")
    else:
        await update.message.reply_text("You are not authorized to use this command.")

# Main function to start the bot
def main():
    # Initialize logging
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(levelname)s - %(message)s')

    application = Application.builder().token(TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("ibanDE", get_and_validate_iban_uk))
    application.add_handler(CommandHandler("ibanFR", get_and_validate_iban_italy))
    application.add_handler(CommandHandler("ibanIT", get_and_validate_iban_france))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_iban))
    application.add_handler(CommandHandler("broadcast", broadcast_command)) # Add broadcast command

    # Start the bot
    application.run_polling()

if __name__ == '__main__':
    main()
