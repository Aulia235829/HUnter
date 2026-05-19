import os
import logging
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import google.generativeai as genai

# Setup Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Mengambil Environment Variables dari Railway
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Inisialisasi AI Gemini
genai.configure(api_key=GEMINI_API_KEY)
ai_model = genai.GenerativeModel('gemini-pro')

# 1. Fitur Utama: Mengambil Data Airdrop Koin Gratis via API
def fetch_crypto_airdrops():
    try:
        # Menggunakan API publik gratis atau bisa diganti dengan scraper/API premium
        # Contoh di bawah menggunakan endpoint mock/publik yang mensimulasikan data airdrop aktual
        url = "https://api.coingecko.com/api/v3/search/trending" # Sebagai basis contoh koin tren baru
        response = requests.get(url, timeout=10).json()
        
        airdrop_msg = "🎁 *Daftar Potensi Airdrop & Koin Gratis Terbaru:* \n\n"
        for idx, coin in enumerate(response['coins'][:5], 1):
            name = coin['item']['name']
            symbol = coin['item']['symbol']
            market_rank = coin['item']['market_cap_rank']
            airdrop_msg += f"{idx}. *{name} ({symbol})*\n   📌 Rank: {market_rank}\n   🔗 Cek cara klaim di komunitas resmi atau scan platform DeFi terkait.\n\n"
        
        airdrop_msg += "💡 *Tips:* Selalu gunakan *burner wallet* (dompet baru) saat melakukan klaim airdrop gratis untuk menjaga keamanan aset utama Anda!"
        return airdrop_msg
    except Exception as e:
        logging.error(f"Error fetching airdrops: {e}")
        return "❌ Gagal mengambil data airdrop terbaru. Silakan coba beberapa saat lagi."

# 2. Handler Perintah /start
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "🤖 *Halo! Saya adalah Bot AI Pemburu Airdrop Mandiri.*\n\n"
        "Gunakan perintah berikut:\n"
        "👉 /airdrop - Untuk mencari info koin gratis & airdrop terbaru.\n\n"
        "Atau jalankan percakapan langsung! *Tanyakan apa saja kepada saya*, dan saya akan menjawabnya secara mandiri menggunakan kecerdasan AI."
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

# 3. Handler Perintah /airdrop
async def airdrop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Sedang memindai jaringan untuk info koin gratis...", parse_mode="Markdown")
    info = fetch_crypto_airdrops()
    await update.message.reply_text(info, parse_mode="Markdown")

# 4. Handler Kemandirian AI (Memproses pertanyaan bebas)
async def handle_ai_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    
    # Prompt rekayasa agar AI bertindak sesuai persona crypto-expert yang mandiri
    system_prompt = f"Anda adalah AI asisten bot Telegram crypto yang mandiri, cerdas, dan solutif. Jawab pertanyaan pengguna berikut dengan ringkas dan jelas: {user_message}"
    
    try:
        # Menghasilkan jawaban AI secara mandiri
        response = ai_model.generate_content(system_prompt)
        await update.message.reply_text(response.text)
    except Exception as e:
        logging.error(f"AI Error: {e}")
        await update.message.reply_text("🧠 Maaf, otak AI saya sedang mengalami gangguan jaringan saat memproses jawaban.")

def main():
    # Inisialisasi Bot Telegram menggunakan Polling (Sangat cocok untuk Railway)
    app = Application.builder().token(BOT_TOKEN).build()

    # Registrasi Command & Message Handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("airdrop", airdrop_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_ai_chat))

    # Mulai menjalankan Bot
    logging.info("Bot sukses dijalankan...")
    app.run_polling()

if __name__ == '__main__':
    main()
