import os
import logging
import asyncio
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from google import genai

# Setup Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not BOT_TOKEN or not GEMINI_API_KEY:
    raise ValueError("ERROR: Token Telegram atau Gemini belum diisi di Railway!")

# Inisialisasi Klien AI Gemini terbaru
ai_client = genai.Client(api_key=GEMINI_API_KEY)

# 1. Fitur Utama: Memindai Tren Airdrop & Alpha dari API Crypto Publik
async def fetch_alpha_trends():
    try:
        # Mengambil data trending market & search volume terbaru dari CoinGecko
        url = "https://api.coingecko.com/api/v3/search/trending"
        loop = asyncio.get_event_loop()
        response_raw = await loop.run_in_executor(None, lambda: requests.get(url, timeout=10))
        response = response_raw.json()
        
        alpha_msg = "🔥 *Crypto Alpha & Trending Report (Jaringan Terdeteksi):* \n\n"
        for idx, coin in enumerate(response['coins'][:5], 1):
            name = coin['item']['name']
            symbol = coin['item']['symbol']
            market_rank = coin['item']['market_cap_rank']
            sparkline = coin['item'].get('data', {}).get('sparkline', 'Tidak tersedia')
            
            alpha_msg += f"{idx}. *{name} ({symbol})*\n"
            alpha_msg += f"   📌 Global Rank: #{market_rank}\n"
            alpha_msg += f"   💡 Potensi Alpha: Proyek ini sedang mengalami lonjakan pencarian on-chain. Periksa komunitas mereka untuk potensi insentif/airdrop tersembunyi.\n\n"
            
        alpha_msg += "🔮 *Tips Intelijen:* Proyek alpha terbaik sering kali dimulai dari diskusi awal di Twitter/X. Gunakan laporan tren di atas sebagai panduan riset mendalam Anda!"
        return alpha_msg
    except Exception as e:
        logging.error(f"Error fetching alpha data: {e}")
        return "❌ Gagal memindai data Alpha terbaru dari server. Silakan coba beberapa saat lagi."

# 2. Handler Perintah /start
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "🤖 *Selamat Datang di Bot Intelijen Crypto & Alpha Hunter!*\n\n"
        "Saya adalah asisten analis mandiri Anda. Gunakan perintah berikut:\n"
        "👉 /alpha - Memindai koin dan proyek yang sedang mengalami lonjakan volume pencarian (Potensi Alpha & Airdrop).\n\n"
        "💬 *Kemandirian AI (Chat Bebas):*\n"
        "Anda bisa mengetik langsung pertanyaan atau kueri spesifik kepada saya, seperti:\n"
        "• _'Apa narasi DeFi yang potensial minggu ini?'_\n"
        "• _'Berikan panduan cara mencari proyek airdrop yang aman dari phising.'_\n"
        "• _'Analisis potensi token layer 2 baru.'_\n\n"
        "Saya akan menganalisis data dan memberikan insight terbaik secara mandiri!"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

# 3. Handler Perintah /alpha
async def alpha_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Memindai metrik on-chain dan volume pencarian crypto terbaru...", parse_mode="Markdown")
    info = await fetch_alpha_trends()
    await update.message.reply_text(info, parse_mode="Markdown")

# 4. Handler Kemandirian AI (Analis Crypto, Tren Twitter, dan Kebijakan Alpha)
async def handle_ai_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    
    # Rekayasa prompt agar AI bertindak sebagai analis handal sesuai dengan spesifikasi tugas Anda
    system_prompt = (
        "Anda adalah AI Asisten Intelijen Crypto, pemburu Alpha, dan penasihat strategi Airdrop yang mandiri, tajam, dan solutif.\n"
        "Tugas utama Anda:\n"
        "1. Membantu mengidentifikasi peluang airdrop, kriteria kelayakan, panduan langkah demi langkah, dan menyaring kebisingan (filtering noise).\n"
        "2. Mendeteksi narasi trending, potensi Alpha (seperti pergerakan whale, proyek baru sebelum mainstream), dan melakukan analisis sentimen pasar.\n"
        "3. Jika ditanya tentang 'eksekusi klaim/menggarap langsung', jelaskan secara edukatif bahwa Anda adalah alat analisis informasi (tidak memegang private key demi keamanan), tetapi Anda sangat kuat dalam mencari data alpha.\n\n"
        f"Jawab kueri spesifik dari pengguna berikut dengan cerdas dan jelas: {user_message}"
    )
    
    max_retries = 3
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            loop = asyncio.get_event_loop()
            
            def call_gemini():
                return ai_client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=system_prompt
                )
                
            response = await loop.run_in_executor(None, call_gemini)
            
            if response and hasattr(response, 'text') and response.text:
                await update.message.reply_text(response.text)
                return
            else:
                await update.message.reply_text("🧠 AI terhubung, tetapi menghasilkan analisis kosong. Coba tanyakan sudut pandang lain.")
                return
                
        except Exception as e:
            if "503" in str(e) and attempt < max_retries - 1:
                logging.warning(f"Server Google padat (Upaya ke-{attempt+1}), mencoba lagi dalam {retry_delay} detik...")
                await asyncio.sleep(retry_delay)
                continue
                
            logging.error(f"⚠️ GEMINI API ERROR: {str(e)}")
            error_message = (
                "🧠 *Otak AI sedang mengalami antrean trafik!*\n\n"
                f"🔍 *Detail Kendala:* `{str(e)}`\n\n"
                "💡 _Saran: Server Free-tier Google sedang padat. Silakan kirim ulang pertanyaan Anda dalam 1 menit ke depan._"
            )
            await update.message.reply_text(error_message, parse_mode="Markdown")
            return

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Registrasi Command & Message Handlers terbaru
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("alpha", alpha_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_ai_chat))
    
    logging.info("Bot Alpha Hunter berbasis Gemini 2.5 berjalan...")
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
