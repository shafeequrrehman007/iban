from aiogram import Bot, Dispatcher, executor, types
import os
import random
import requests
from bs4 import BeautifulSoup
import logging
from dotenv import load_dotenv
from typing import Optional, Dict, Any
import asyncio

# Load environment variables
load_dotenv()

# Bot token
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN environment variable is not set")

# File paths for IBANs
IBAN_FILES = {
    'uk': 'iban.txt',
    'italy': 'iban2.txt',
    'france': 'iban3.txt'
}

# File to store user IDs
USER_FILE = 'users.txt'

# Base URL for IBAN validation API
BASE_URL = "https://ibanapi.com"

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class IBANValidator:
    def __init__(self):
        self.session = requests.Session()
        self.proxies = self._get_proxies()

    def _get_proxies(self) -> Optional[Dict[str, str]]:
        """Get proxy configuration from environment variables."""
        proxy_url = os.getenv("PROXY_URL")
        if not proxy_url:
            return None
        return {
            "http": proxy_url,
            "https": proxy_url
        }

    def get_random_iban_from_file(self, country: str) -> Optional[str]:
        """Retrieve a random IBAN from the specified country's file."""
        file_path = IBAN_FILES.get(country)
        if not file_path:
            logger.error(f"Invalid country: {country}")
            return None

        try:
            with open(file_path, 'r') as file:
                ibans = file.readlines()
            return random.choice(ibans).strip()
        except FileNotFoundError:
            logger.error(f"IBAN file not found: {file_path}")
            return None
        except Exception as e:
            logger.error(f"Error reading IBAN file: {e}")
            return None

    def validate_iban(self, iban: str) -> Optional[Dict[str, Any]]:
        """Validate IBAN using the external API."""
        token_url = f"{BASE_URL}/iban-checker"
        validate_url = f"{BASE_URL}/validate-iban/{iban}"

        try:
            # Fetch CSRF token
            response = self.session.get(token_url, proxies=self.proxies)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching CSRF token: {e}")
            return None

        # Extract CSRF token
        soup = BeautifulSoup(response.text, "html.parser")
        csrf_token_meta = soup.find("meta", {"name": "csrf-token"})
        if not csrf_token_meta:
            logger.error("CSRF token not found in the response")
            return None

        headers = {
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "en-US,en;q=0.9",
            "Origin": BASE_URL,
            "Referer": token_url,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "X-CSRF-TOKEN": csrf_token_meta["content"],
            "X-Requested-With": "XMLHttpRequest"
        }

        try:
            response = self.session.post(validate_url, headers=headers, proxies=self.proxies)
            response.raise_for_status()
            data = response.json()
        except (requests.exceptions.RequestException, ValueError) as e:
            logger.error(f"Error validating IBAN: {e}")
            return None

        if data.get("result") == 200:
            bank_account = data["data"].get("bank_account")
            if bank_account:
                return {
                    "status": "success",
                    "iban": iban,
                    "message": data.get("message"),
                    "bank_account": bank_account,
                    "country_code": data["data"].get("country_code", "N/A"),
                    "country_name": data["data"].get("country_name", "N/A"),
                    "currency_code": data["data"].get("currency_code", "N/A"),
                    "bank_name": data["data"].get("bank", {}).get("bank_name", "N/A"),
                    "bic": data["data"].get("bank", {}).get("bic", "N/A")
                }
        return {
            "status": "failure",
            "iban": iban,
            "message": data.get("message", "Unknown error occurred.")
        }

class UserManager:
    @staticmethod
    async def save_user(user_id: int) -> bool:
        """Save user ID to file if not already present."""
        try:
            with open(USER_FILE, 'a+') as f:
                f.seek(0)
                if str(user_id) + '\n' not in f.readlines():
                    f.write(str(user_id) + '\n')
                    logger.info(f"Saved new user ID: {user_id}")
                    return True
                return False
        except Exception as e:
            logger.error(f"Error saving user ID {user_id}: {e}")
            return False

    @staticmethod
    def get_user_ids() -> list:
        """Read all user IDs from file."""
        try:
            with open(USER_FILE, 'r') as f:
                return [int(line.strip()) for line in f.readlines()]
        except FileNotFoundError:
            logger.warning("User file not found. No users loaded.")
            return []
        except Exception as e:
            logger.error(f"Error reading user IDs: {e}")
            return []

class TelegramBot:
    def __init__(self):
        self.bot = Bot(token=TOKEN)
        self.dp = Dispatcher(self.bot)
        self.validator = IBANValidator()
        self.user_manager = UserManager()
        self.setup_handlers()

    def setup_handlers(self):
        """Set up all message handlers."""
        self.dp.message_handler(commands=['start'])(self.start)
        self.dp.message_handler(commands=['ibanDE'])(self.get_and_validate_iban_uk)
        self.dp.message_handler(commands=['ibanFR'])(self.get_and_validate_iban_france)
        self.dp.message_handler(commands=['ibanIT'])(self.get_and_validate_iban_italy)
        self.dp.message_handler(lambda message: message.text.startswith('.chk'))(self.check_iban)

    async def start(self, message: types.Message):
        """Handle /start command."""
        user_id = message.from_user.id
        username = message.from_user.username
        chat_id = message.chat.id
        
        welcome_message = (
            f"Welcome to IBAN Generator and Validator!\n"
            f"Username: @{username}\n"
            f"User ID: {chat_id}\n\n"
            f"Get IBAN and validate with commands:\n"
            f"/ibanDE - Get UK IBAN\n"
            f"/ibanFR - Get French IBAN\n"
            f"/ibanIT - Get Italian IBAN\n\n"
            f"Validate IBAN with: .chk <iban>"
        )
        
        await message.reply(welcome_message)
        await self.user_manager.save_user(user_id)

    async def show_loading(self, message: types.Message, text: str):
        """Show loading message with animated dots."""
        loading_message = await message.reply(f"{text} ⏳")
        for _ in range(3):
            await asyncio.sleep(1)
            await loading_message.edit_text(f"{text} {'⏳' * (_ + 1)}")
        return loading_message

    async def get_and_validate_iban(self, message: types.Message, country: str):
        """Generic handler for getting and validating IBANs."""
        # Show initial loading message
        loading_msg = await self.show_loading(message, "🔍 Searching for IBAN")
        
        iban = self.validator.get_random_iban_from_file(country)
        if not iban:
            await loading_msg.edit_text(f"❌ Could not retrieve IBAN from {country} file.")
            return

        # Show validation loading message
        await loading_msg.edit_text("🔍 Validating IBAN")
        for _ in range(2):
            await asyncio.sleep(1)
            await loading_msg.edit_text(f"🔍 Validating IBAN {'⏳' * (_ + 1)}")

        result = self.validator.validate_iban(iban)
        if not result:
            await loading_msg.edit_text(f"❌ Error validating IBAN from {country} file.")
            return

        response_message = self.format_validation_response(result)
        await loading_msg.edit_text(response_message)

    async def get_and_validate_iban_uk(self, message: types.Message):
        await self.get_and_validate_iban(message, 'uk')

    async def get_and_validate_iban_france(self, message: types.Message):
        await self.get_and_validate_iban(message, 'france')

    async def get_and_validate_iban_italy(self, message: types.Message):
        await self.get_and_validate_iban(message, 'italy')

    async def check_iban(self, message: types.Message):
        """Handle IBAN validation requests."""
        iban = message.text[5:].strip()
        if not iban:
            await message.reply("Please provide an IBAN after .chk (e.g., .chk GB29NWBK60161331926819)")
            return

        # Show validation loading message
        loading_msg = await self.show_loading(message, "🔍 Validating IBAN")
        
        result = self.validator.validate_iban(iban)
        if not result:
            await loading_msg.edit_text("❌ Error validating IBAN.")
            return

        response_message = self.format_validation_response(result)
        await loading_msg.edit_text(response_message)

    @staticmethod
    def format_validation_response(result: Dict[str, Any]) -> str:
        """Format the IBAN validation response."""
        if result["status"] == "success":
            return (
                f"✅ IBAN Validation Successful!\n\n"
                f"📝 Details:\n"
                f"IBAN: `{result['iban']}`\n"
                f"Message: {result['message']}\n"
                f"Bank Account: {result['bank_account']}\n"
                f"Country Code: {result['country_code']}\n"
                f"Country Name: {result['country_name']}\n"
                f"Currency Code: {result['currency_code']}\n"
                f"Bank Name: {result['bank_name']}\n"
                f"BIC: `{result['bic']}`"
            )
        return f"❌ `{result['iban']}` - {result['message']}"

def main():
    """Initialize and start the bot."""
    bot = TelegramBot()
    executor.start_polling(bot.dp, skip_updates=True)

if __name__ == '__main__':
    main()
