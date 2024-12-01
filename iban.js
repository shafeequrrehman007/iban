const TelegramBot = require('node-telegram-bot-api');
const axios = require('axios');
const fs = require('fs');
const cheerio = require('cheerio');

// Bot Token
const TOKEN = '6685826015:AAFet4wAr4r_Jt5U0aYcxe6fmKL1o_jWqGM';
const bot = new TelegramBot(TOKEN, { polling: true });

// File paths for IBANs
const ibanFilePathUK = 'iban.txt';
const ibanFilePathItaly = 'iban2.txt';
const ibanFilePathFrance = 'iban3.txt';

// Proxy configuration (optional)
const proxy = {
  proxy: {
    host: 'p.webshare.io',
    port: 80,
    auth: {
      username: 'tcnppbwe-rotate',
      password: 'm27wwonyzdza'
    }
  }
};

// Function to get a random IBAN from file
const getRandomIbanFromFile = (filePath) => {
  try {
    const ibans = fs.readFileSync(filePath, 'utf-8').split('\n').filter(Boolean);
    const randomIban = ibans[Math.floor(Math.random() * ibans.length)];
    return `Valid IBAN: ${randomIban}`;
  } catch (err) {
    console.error(err);
    return 'IBAN file not found.';
  }
};

// Function to validate IBAN using API
const validateIban = async (iban) => {
  const baseUrl = 'https://ibanapi.com';
  const tokenUrl = `${baseUrl}/iban-checker`;
  const validateUrl = `${baseUrl}/validate-iban/${iban}`;

  try {
    const tokenResponse = await axios.get(tokenUrl, proxy);
    const $ = cheerio.load(tokenResponse.data);
    const csrfToken = $('meta[name="csrf-token"]').attr('content');

    if (!csrfToken) throw new Error('CSRF token not found.');

    const headers = {
      'Accept': '*/*',
      'User-Agent': 'Mozilla/5.0',
      'X-CSRF-TOKEN': csrfToken,
      'X-Requested-With': 'XMLHttpRequest'
    };

    const validateResponse = await axios.post(validateUrl, {}, { headers, ...proxy });

    if (validateResponse.data.result === 200) {
      const data = validateResponse.data.data;
      return {
        status: 'success',
        iban,
        message: validateResponse.data.message,
        bankAccount: data.bank_account,
        countryCode: data.country_code || 'N/A',
        countryName: data.country_name || 'N/A',
        currencyCode: data.currency_code || 'N/A',
        bankName: data.bank?.bank_name || 'N/A',
        bic: data.bank?.bic || 'N/A'
      };
    } else {
      return { status: 'failure', iban, message: validateResponse.data.message || 'Unknown error occurred.' };
    }
  } catch (error) {
    console.error('Error validating IBAN:', error);
    return { status: 'error', iban, message: 'Failed to validate IBAN.' };
  }
};

// Command Handlers
bot.onText(/\/start/, (msg) => {
  const chatId = msg.chat.id;
  const username = msg.from.username || 'User';
  bot.sendMessage(chatId, `Welcome to IBAN Generator and Validator!\nUsername: @${username}\nUser ID: ${chatId}\n\nGet IBAN or validate with commands:\n/getiban`);
});

bot.onText(/\/getiban/, (msg) => {
  const chatId = msg.chat.id;
  const message = `
GB & UK IBAN: /ibanUK
ITALY IBAN: /ibanIT
FRANCE IBAN: /ibanFR
Validate IBAN with: .chk <iban>
  `;
  bot.sendMessage(chatId, message);
});

bot.onText(/\/ibanUK/, (msg) => {
  const iban = getRandomIbanFromFile(ibanFilePathUK);
  bot.sendMessage(msg.chat.id, iban);
});

bot.onText(/\/ibanIT/, (msg) => {
  const iban = getRandomIbanFromFile(ibanFilePathItaly);
  bot.sendMessage(msg.chat.id, iban);
});

bot.onText(/\/ibanFR/, (msg) => {
  const iban = getRandomIbanFromFile(ibanFilePathFrance);
  bot.sendMessage(msg.chat.id, iban);
});

bot.onText(/\.chk (.+)/, async (msg, match) => {
  const chatId = msg.chat.id;
  const iban = match[1].trim();
  const result = await validateIban(iban);

  if (result.status === 'success') {
    bot.sendMessage(chatId, `IBAN Validation Successful! ✅\nIBAN: ${result.iban}\nMessage: ${result.message}\nBank Account: ${result.bankAccount}\nCountry Code: ${result.countryCode}\nCountry Name: ${result.countryName}\nCurrency Code: ${result.currencyCode}\nBank Name: ${result.bankName}\nBIC: ${result.bic}`);
  } else {
    bot.sendMessage(chatId, `❌ ${result.iban} - ${result.message}`);
  }
});
