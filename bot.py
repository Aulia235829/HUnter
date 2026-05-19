import os
import logging
import asyncio
import requests
import io
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from google import genai
from google.genai import errors

# Setup Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not BOT_TOKEN or not GEMINI_API_KEY:
    raise ValueError("ERROR: Token Telegram atau Gemini belum diisi di Railway!")

# Inisialisasi Klien AI Gemini
ai_client = genai.Client(api_key=GEMINI_API_KEY)

# Fungsi Memotong Teks Panjang untuk Batasan Telegram
def split_message(text, max_length=4000):
    if len(text) <= max_length:
        return [text]
    parts = []
    while text:
        if len(text) <= max_length:
            parts.append(text)
            break
        split_at = text.rfind('\n', 0, max_length)
        if split_at == -1:
            split_at = text.rfind(' ', 0, max_length)
            if split_at == -1:
                split_at = max_length
        parts.append(text[:split_at])
        text = text[split_at:].lstrip()
    return parts

# Fitur Utama: Memindai Tren Pasar via API Publik
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
            alpha_msg += f"{idx}. *{name} ({symbol})*\n   📌 Global Rank: #{market_rank}\n\n"
        return alpha_msg
    except Exception:
        return "❌ Gagal memindai data tren terbaru."

# Handler Perintah /start
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "🤖 *Selamat Datang di Bot Asisten Crypto & AI Generator Mandiri!*\n\n"
        "🎨 *Cara Membuat Gambar:* \n"
        "Ketik pesan diawali kata *buatkan gambar* atau *draw*, contoh:\n"
        "• _buatkan gambar maskot crypto elang 3D neon_\n\n"
        "💬 *Chat Teks:* Tanyakan apa saja bebas, saya akan menjawab mandiri."
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

# Handler Perintah /alpha
async def alpha_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Memindai metrik crypto terbaru...", parse_mode="Markdown")
    info = await fetch_alpha_trends()
    await update.message.reply_text(info, parse_mode="Markdown")

# Handler Utama: Mengatur Percakapan Teks & Pembuatan Gambar Otomatis
async def handle_ai_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    user_message_lower = user_message.lower()
    
    # ─── JALUR GENERATE GAMBAR ───
    if user_message_lower.startswith("buatkan gambar") or user_message_lower.startswith("draw"):
        # Ambil deskripsi bersih
        prompt_gambar = user_message.replace("buatkan gambar", "").replace("buatkan Gambar", "").replace("draw", "").replace("Draw", "").strip()
        
        if not prompt_gambar:
            await update.message.reply_text("⚠️ Tolong masukkan deskripsi gambar setelah kata kunci. Contoh: `buatkan gambar kucing terbang`")
            return

        await update.message.reply_text(f"🎨 *Sedang melukis secara mandiri untuk:* _{prompt_gambar}_\n_Mohon tunggu sebentar..._", parse_mode="Markdown")
        
        try:
            loop = asyncio.get_event_loop()
            
            # Memanggil fungsi generator gambar menggunakan model Imagen 3 terbaru
            def generate_image():
                return ai_client.models.generate_images(
                    model='imagen-3.0-generate-002',
                    prompt=prompt_gambar,
                    config=dict(
                        number_of_images=1,
                        aspect_ratio="1:1"
                    )
                )
                
            result = await loop.run_in_executor(None, generate_image)
            
            # Mengonversi dan membaca byte gambar agar dikirim sebagai file foto asli
            if result and result.generated_images:
                for generated_image in result.generated_images:
                    # Mengambil data byte gambar secara aman
                    raw_bytes = generated_image.image.image_bytes
                    image_file = io.BytesIO(raw_bytes)
                    image_file.name = 'ai_generation.jpg'
                    
                    # Kirim file foto langsung ke Telegram
                    await update.message.reply_photo(photo=image_file, caption=f"✨ Hasil kreasi mandiri untuk: *{prompt_gambar}*", parse_mode="Markdown")
                    return
            else:
                await update.message.reply_text("⚠️ Google tidak mengembalikan data gambar. Pastikan deskripsi Anda sudah jelas.")
                return
                
        except errors.APIError as api_err:
            logging.error(f"Safety Blocked: {api_err}")
            await update.message.reply_text("⚠️ *Permintaan Gambar Ditolak:* Deskripsi mengandung kata sensitif/vulgar yang melanggar batas keamanan otomatis Google AI Studio.")
            return
        except Exception as e:
            logging.error(f"Image Error: {str(e)}")
            await update.message.reply_text(f"❌ *Gagal memproses gambar:* `{str(e)}`")
            return

    # ─── JALUR CHAT TEKS BIASA ───
    system_prompt = (
        "Anda adalah AI Asisten Crypto Serbabisa yang mandiri dan solutif. "
        f"Jawab pertanyaan pengguna dengan cerdas: {user_message}"
    )
    
    max_retries = 3
    retry_delay = 2
    for attempt in range(max_retries):
        try:
            loop = asyncio.get_event_loop()
            def call_gemini():
                return ai_client.models.generate_content(model='gemini-2.5-flash', contents=system_prompt)
            response = await loop.run_in_executor(None, call_gemini)
            
            if response and hasattr(response, 'text') and response.text:
                message_parts = split_message(response.text)
                for part in message_parts:
                    try:
                        await update.message.reply_text(part, parse_mode="Markdown")
                    except Exception:
                        await update.message.reply_text(part)
                    await asyncio.sleep(0.5)
                return
            else:
                await update.message.reply_text("🧠 Respons kosong. Coba ulangi.")
                return
        except Exception as e:
            if "503" in str(e) and attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
                continue
            await update.message.reply_text(f"🧠 *Otak AI kendala:* `{str(e)}`")
            return

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("alpha", alpha_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_ai_chat))
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
