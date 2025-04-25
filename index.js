const { Telegraf } = require('telegraf');
const axios = require('axios');
const cheerio = require('cheerio');
const fs = require('fs');
require('dotenv').config();

// Load environment variables
const TOKEN = process.env.BOT_TOKEN;
const iban_file_path_uk = 'iban.txt';
const iban_file_path_italy = 'iban2.txt';
const iban_file_path_france = 'iban3.txt';
const base_url = "https://ibanapi.com";
const proxies = {
    http: process.env.HTTP_PROXY || undefined,
    https: process.env.HTTPS_PROXY || undefined,
};

// User data store (in-memory for simplicity - use a database for production)
let userIds = new Set();

// Function to retrieve a random IBAN from a file
function get_random_iban_from_file(file_path) {
    try {
        const data = fs.readFileSync(file_path, 'utf8');
        const ibans = data.split('\n').map(line => line.trim()).filter(line => line !== '');
        if (ibans.length === 0) {
            console.warn(`No IBANs found in file: ${file_path}`);
            return null;
        }
        const random_iban = ibans[Math.floor(Math.random() * ibans.length)];
        return random_iban;
    } catch (error) {
        console.error(`Error reading file ${file_path}:`, error);
        return null;
    }
}

// Function to validate IBAN using the external API
async function validate_iban(iban) {
    const token_url = `${base_url}/iban-checker`;
    const validate_url = `${base_url}/validate-iban/${iban}`;

    const axiosConfig = {
        headers: {
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "en-US,en;q=0.9",
            "Origin": base_url,
            "Referer": token_url,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "X-Requested-With": "XMLHttpRequest"
        }
    };

    if (proxies.http || proxies.https) {
        axiosConfig.proxy = false;

        const proxyUrl = proxies.http || proxies.https;

        try {
            const url = new URL(proxyUrl);
            axiosConfig.proxy = {
                host: url.hostname,
                port: parseInt(url.port),
                auth: url.username && url.password ? { username: url.username, password: url.password } : undefined,
            };
        } catch (error) {
            console.error("Error parsing proxy URL.  Please check your .env file:", error);
            return null;
        }
    }

    try {
        const tokenResponse = await axios.get(token_url, axiosConfig);
        const $ = cheerio.load(tokenResponse.data);
        const csrf_token = $('meta[name="csrf-token"]').attr('content');

        if (!csrf_token) {
            console.error("CSRF token not found in the response.");
            return null;
        }

        axiosConfig.headers["X-CSRF-TOKEN"] = csrf_token;
        const validationResponse = await axios.post(validate_url, {}, axiosConfig);
        const data = validationResponse.data;

        if (data.result === 200) {
            const bank_account = data.data.bank_account;
            if (bank_account) {
                return {
                    status: "success",
                    iban: iban,
                    message: data.message,
                    bank_account: bank_account,
                    country_code: data.data.country_code || "N/A",
                    country_name: data.data.country_name || "N/A",
                    currency_code: data.data.currency_code || "N/A",
                    bank_name: data.data.bank?.bank_name || "N/A",
                    bic: data.data.bank?.bic || "N/A"
                };
            } else {
                return {status: "failure", iban: iban, message: "IBAN is invalid."};
            }
        } else {
            return {status: "failure", iban: iban, message: data.message || "Unknown error occurred."};
        }
    } catch (error) {
        console.error("Error validating IBAN:", error.message);

        if (error.response) {
            console.error("API Response Data:", error.response.data);
            console.error("API Response Status:", error.response.status);
            console.error("API Response Headers:", error.response.headers);
        } else if (error.request) {
            console.error("No response received. Request details:", error.request);
        } else {
            console.error("Error setting up the request:", error.message);
        }

        return null;
    }
}

// Function to format the IBAN validation response
function format_validation_response(result) {
    if (result.status === "success") {
        return (
            `IBAN Validation Successful! ✅\n` +
            `IBAN: ${result.iban}\n` +
            `Message: ${result.message}\n` +
            `Bank Account: ${result.bank_account}\n` +
            `Country Code: ${result.country_code}\n` +
            `Country Name: ${result.country_name}\n` +
            `Currency Code: ${result.currency_code}\n` +
            `Bank Name: ${result.bank_name}\n` +
            `BIC: ${result.bic}`
        );
    } else {
        return `❌ ${result.iban} - ${result.message}`;
    }
}

// Function to broadcast a message to all users
async function broadcast(bot, message) {
    for (const userId of userIds) {
        try {
            await bot.telegram.sendMessage(userId, message);
        } catch (error) {
            console.error(`Failed to send message to user ${userId}:`, error);
            // Consider removing the user from the list if sending consistently fails.
            // userIds.delete(userId); //  Uncomment with caution as it may indicate a block.
        }
    }
}

// Create a new Telegraf bot
const bot = new Telegraf(TOKEN);

// Middleware to track user IDs
bot.use((ctx, next) => {
    const userId = ctx.from?.id;
    if (userId) {
        userIds.add(userId); // Add user ID to the set
    }
    return next();
});

// Start command handler
bot.start((ctx) => {
    const username = ctx.message.from.username;
    const chatId = ctx.message.chat.id;
    const message = `Welcome to IBAN Generator and Validator!\nUsername: @${username}\nUser ID: ${chatId}\n\nGet IBAN and validate with commands:\n/ibanDE\n/ibanFR\n/ibanIT\n\nValidate IBAN with: .chk <iban>`;
    ctx.reply(message);
});

// /ibanDE command handler
bot.command('ibanDE', async (ctx) => {
    const iban = get_random_iban_from_file(iban_file_path_uk);
    if (iban) {
        const result = await validate_iban(iban);
        if (result) {
            const response_message = format_validation_response(result);
            ctx.reply(response_message);
        } else {
            ctx.reply("Error validating IBAN from UK file.");
        }
    } else {
        ctx.reply("Could not retrieve IBAN from UK file.");
    }
});

// /ibanFR command handler
bot.command('ibanFR', async (ctx) => {
    const iban = get_random_iban_from_file(iban_file_path_italy);
    if (iban) {
        const result = await validate_iban(iban);
        if (result) {
            const response_message = format_validation_response(result);
            ctx.reply(response_message);
        } else {
            ctx.reply("Error validating IBAN from Italy file.");
        }
    } else {
        ctx.reply("Could not retrieve IBAN from Italy file.");
    }
});

// /ibanIT command handler
bot.command('ibanIT', async (ctx) => {
    const iban = get_random_iban_from_file(iban_file_path_france);
    if (iban) {
        const result = await validate_iban(iban);
        if (result) {
            const response_message = format_validation_response(result);
            ctx.reply(response_message);
        } else {
            ctx.reply("Error validating IBAN from France file.");
        }
    } else {
        ctx.reply("Could not retrieve IBAN from France file.");
    }
});

// IBAN validation handler using .chk prefix
bot.hears(/^.chk\s+(.*)$/i, async (ctx) => {
    const iban = ctx.match[1].trim();
    const result = await validate_iban(iban);

    if (result) {
        const response_message = format_validation_response(result);
        ctx.reply(response_message);
    } else {
        ctx.reply("Error validating IBAN.");
    }
});

// /broadcast command (ADMIN ONLY - implement proper authentication!)
bot.command('broadcast', async (ctx) => {
    const message = ctx.message.text.substring(11).trim(); // Extract message from command

    // Basic admin check (replace with proper authentication)
    const adminUserId = process.env.ADMIN_USER_ID; // Store admin user ID in .env
    if (ctx.from.id.toString() !== adminUserId) {
        return ctx.reply("Unauthorized.  You are not an admin.");
    }

    if (!message) {
        return ctx.reply("Please provide a message to broadcast.");
    }

    await broadcast(bot, message);
    ctx.reply("Broadcast sent!");
});

// Launch the bot
if (!TOKEN) {
    console.error("Bot token is missing!  Please set the BOT_TOKEN environment variable.");
    process.exit(1);
}

bot.launch()
    .then(() => {
        console.log("Bot is running!");
    })
    .catch((err) => {
        console.error("Failed to launch bot:", err);
        process.exit(1);
    });

// Enable graceful stop
process.once('SIGINT', () => bot.stop('SIGINT'));
process.once('SIGTERM', () => bot.stop('SIGTERM'));
