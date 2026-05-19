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

# Fungsi Memotong Teks Panjang agar Aman dari Limit Telegram (Max 4000 char per part)
def split_message(text, max_length=4000):
    if len(text) <= max_length:
        return [text]
    
    parts = []
    while text:
        if len(text) <= max_length:
            parts.append(text)
            break
        
        # Cari batas potongan terbaik pada karakter baris baru (\n) agar teks rapi
        split_at = text.rfind('\n', 0, max_length)
        if split_at == -1:
            # Jika tidak ada baris baru, cari potongan pada spasi terakhir
            split_at = text.rfind(' ', 0, max_length)
            if split_at == -1:
                split_at = max_length
        
        parts.append(text[:split_at])
        text = text[split_at:].lstrip()
    return parts

# 1. Fitur Utama: Memindai Tren Pasar via API Publik
async def fetch_alpha_trends():
    try:
        url = "https://api.coingecko.com/api/v3/search/trending"
        loop = asyncio.get_event_loop()
        response_raw = await loop.run_in_executor(None, lambda: requests.get(url, timeout=10))
        response = response_raw.json()
        
        alpha_msg = "🔥 *Crypto Alpha & Trending Report:* \n\n"
        for idx, coin in enumerate(response['coins'][:5], 1):
            name = coin['item']['name']
            symbol = coin['item']['symbol']
            market_rank = coin['item']['market_cap_rank']
            
            alpha_msg += f"{idx}. *{name} ({symbol})*\n"
            alpha_msg += f"   📌 Global Rank: #{market_rank}\n"
            alpha_msg += f"   💡 Potensi Alpha: Koin ini sedang mengalami lonjakan pencarian. Periksa ekosistemnya untuk potensi insentif atau airdrop tersembunyi.\n\n"
            
        alpha_msg += "🔮 *Tips:* Gunakan data tren di atas sebagai titik awal untuk riset mendalam Anda di media sosial."
        return alpha_msg
    except Exception as e:
        logging.error(f"Error fetching alpha data: {e}")
        return "❌ Gagal memindai data tren terbaru dari server. Silakan coba beberapa saat lagi."

# 2. Handler Perintah /start
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "🤖 *Selamat Datang di Bot Asisten Crypto Serbabisa & Mandiri!*\n\n"
        "Saya siap membantu Anda melakukan apa saja di dunia crypto tanpa batas aturan yang kaku. "
        "Gunakan perintah utama:\n"
        "👉 /alpha - Memindai koin dan proyek yang sedang trending saat ini.\n\n"
        "💬 *Kemandirian AI Penuh (Ketik Perintah / Tanya Apa Saja):*\n"
        "Anda bisa menyuruh saya melakukan tugas-tugas teknis maupun strategis langsung lewat chat biasa, contohnya:\n"
        "🛠️ *Teknis:* _'Buatkan skrip python untuk generate multi-wallet BSC'_ atau _'Bagaimana cara setup wallet EVM yang aman?'_\n"
        "🚰 *Faucet:* _'Berikan rekomendasi taktik mencari faucet koin gratisan testnet'_\n"
        "📈 *Analisis:* _'Saring narasi crypto Alpha minggu ini'_\n\n"
        "Silakan perintahkan apa saja, dan saya akan memprosesnya secara mandiri dengan kecerdasan AI!"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

# 3. Handler Perintah /alpha
async def alpha_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Memindai metrik on-chain dan volume pencarian crypto terbaru...", parse_mode="Markdown")
    info = await fetch_alpha_trends()
    await update.message.reply_text(info, parse_mode="Markdown")

# 4. Handler Kemandirian AI Total (Dilengkapi Fitur Auto-Splitting Pesan Panjang)
async def handle_ai_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    system_prompt = (
        "Anda adalah AI Asisten Crypto Serbabisa yang mandiri, cerdas, solutif, dan ahli dalam urusan teknis maupun strategis.\n"
        "Anda memiliki kemandirian penuh untuk menjawab, menginstruksikan, dan membantu pengguna dalam segala skenario perintah:\n"
        "1. Jika pengguna meminta dibuatkan wallet crypto atau multi-wallet, berikan penjelasan langkah amannya, dan jika perlu buatkan contoh kode/skrip pemrograman (seperti Python menggunakan web3.py) yang bisa mereka jalankan sendiri secara lokal demi keamanan.\n"
        "2. Jika pengguna meminta rekomendasi link Faucet atau koin gratis, berikan taktik berburu faucet terbaik, sebutkan nama platform aggregator/faucet tepercaya (seperti tautan faucet testnet resmi, faucet jaringan TON/EVM), serta berikan trik agar tidak terkena jebakan phising.\n"
        "3. Bertindaklah sebagai filter kebisingan (noise filter) yang tajam untuk menyajikan intisari alpha, pergerakan paus (whale), tren Twitter/X, dan rencana kerja harian untuk berburu kripto.\n"
        "4. Selalu gunakan gaya bahasa yang lugas, profesional, mudah dipahami, dan langsung memberikan solusi praktis.\n\n"
        f"Eksekusi secara mandiri perintah atau pertanyaan dari pengguna berikut: {user_message}"
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
                # EKSEKUSI PEMOTONGAN TEKS JIKA TERLALU PANJANG
                message_parts = split_message(response.text)
                
                for part in message_parts:
                    # Cek jika ada format markdown yang tidak tertutup akibat pemotongan agar tidak error
                    try:
                        await update.message.reply_text(part, parse_mode="Markdown")
                    except Exception:
                        # Fallback jika parsing markdown error setelah teks dipotong
                        await update.message.reply_text(part)
                    await asyncio.sleep(0.5) # Jeda setengah detik agar tidak terkena spam-limit Telegram
                return
            else:
                await update.message.reply_text("🧠 AI terhubung, tetapi menghasilkan respons kosong. Coba ulangi perintah Anda.")
                return
                
        except Exception as e:
            if "503" in str(e) and attempt < max_retries - 1:
                logging.warning(f"Server Google padat (Upaya ke-{attempt+1}), mencoba lagi dalam {retry_delay} detik...")
                await asyncio.sleep(retry_delay)
                continue
                
            logging.error(f"⚠️ GEMINI API ERROR: {str(e)}")
            error_message = (
                "🧠 *Otak AI sedang mengalami kendala!*\n\n"
                f"🔍 *Detail Kendala:* `{str(e)}`\n\n"
                "💡 _Saran: Silakan kirim ulang perintah Anda dalam beberapa saat._"
            )
            await update.message.reply_text(error_message, parse_mode="Markdown")
            return

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("alpha", alpha_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_ai_chat))
    
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
