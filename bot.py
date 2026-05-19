import os
import logging
import asyncio
import requests
import io
import json
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from google import genai
from google.genai import errors
from google.genai import types

# Import Playwright untuk Otomasi Pengisian Situs Web
from playwright.async_api import async_playwright

# Setup Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Data Profil Anda di Railway Variables
MY_PROFILE_DATA = {
    "TWITTER_USERNAME": os.getenv("MY_TWITTER_USER", "@UserTwitter"),
    "TELEGRAM_USERNAME": os.getenv("MY_TELEGRAM_USER", "@UserTelegram"),
    "GMAIL_ADDRESS": os.getenv("MY_GMAIL", "user@gmail.com"),
    "CRYPTO_WALLET_ADDRESS": os.getenv("MY_WALLET_ADD", "0x0000..."),
    "FULL_NAME": os.getenv("MY_FULL_NAME", "Ilham Aulia")
}

if not BOT_TOKEN or not GEMINI_API_KEY:
    raise ValueError("ERROR: Token Telegram atau Gemini belum diisi di Railway!")

# Inisialisasi Klien AI Gemini
ai_client = genai.Client(api_key=GEMINI_API_KEY)

# Fungsi Memotong Teks Panjang untuk Telegram
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

# 🧠 LOGIKA PINTAR: Menggunakan gemini-1.5-flash untuk kuota melimpah
async def smart_ai_analyze_and_fill(url):
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            await page.goto(url, timeout=30000)
            await page.wait_for_load_state("networkidle")
            
            inputs = await page.query_selector_all("input, textarea, select")
            form_structure = []
            
            for idx, field in enumerate(inputs):
                tag_name = await field.evaluate("el => el.tagName.toLowerCase()")
                type_attr = await field.get_attribute("type") or "text"
                placeholder = await field.get_attribute("placeholder") or ""
                name_attr = await field.get_attribute("name") or ""
                id_attr = await field.get_attribute("id") or ""
                
                form_structure.append({
                    "index": idx,
                    "tag": tag_name,
                    "type": type_attr,
                    "placeholder": placeholder,
                    "name": name_attr,
                    "id": id_attr
                })
            
            if not form_structure:
                await browser.close()
                return "⚠️ Bot tidak menemukan kolom input teks apa pun di dalam situs web tersebut."

            loop = asyncio.get_event_loop()
            system_prompt = (
                "Anda adalah AI Detektif Formulir Web. Tugas Anda adalah mencocokkan kolom input situs web dengan data profil pengguna.\n"
                f"Data Profil Pengguna yang Tersedia: {json.dumps(MY_PROFILE_DATA)}\n\n"
                f"Struktur Formulir Situs Web: {json.dumps(form_structure)}\n\n"
                "Instruksi:\n"
                "Analisis setiap kolom input berdasarkan 'placeholder', 'name', atau 'id'-nya. Tentukan data profil mana yang paling cocok dimasukkan ke kolom tersebut.\n"
                "Kembalikan jawaban dalam format JSON murni berbentuk list/array objek seperti contoh ini (jangan beri teks penjelasan tambahan):\n"
                '[{"index": 0, "fill_value": "nilai_data_profil", "detected_as": "Alamat Wallet"}, {"index": 1, "fill_value": "nilai_data_profil", "detected_as": "Username Twitter"}]'
            )
            
            def call_gemini_analysis():
                res = ai_client.models.generate_content(model='gemini-1.5-flash', contents=system_prompt)
                return res.text.strip() if res.text else "[]"
                
            ai_decision_text = await loop.run_in_executor(None, call_gemini_analysis)
            
            # --- PERBAIKAN BARIS 107 (MENGGUNAKAN STRIP & REPLACE YANG AMAN) ---
            ai_decision_text = ai_decision_text.strip("`").replace("json", "").strip()

            decisions = json.loads(ai_decision_text)
            report_details = ""
            
            for action in decisions:
                idx = action["index"]
                val_to_fill = action["fill_value"]
                detected_type = action["detected_as"]
                
                if not val_to_fill or val_to_fill in ["", "none", "null"]:
                    continue
                
                await inputs[idx].fill(val_to_fill)
                report_details += f"• Kolom terdeteksi sebagai *{detected_type}* -> Berhasil diisi secara pintar.\n"

            submit_btn = await page.query_selector("button[type='submit'], input[type='submit'], .submit-btn, button:has-text('Join'), button:has-text('Register'), button:has-text('Submit')")
            if submit_btn and report_details:
                await submit_btn.click()
                await asyncio.sleep(3)
                report_details += "• *Tombol Submit / Kirim:* Berhasil dideteksi dan diklik otomatis.\n"
            
            await browser.close()
            
            if report_details:
                return f"✅ *Analisis Pintar AI & Pengisian Selesai!*\n\n🌐 *Situs:* {url}\n\n📊 *Laporan Deteksi Otomatis:*\n{report_details}\n📌 *Status:* Formulir airdrop Anda sudah dikirim oleh bot."
            else:
                return "⚠️ AI berhasil menganalisis situs, tetapi memutuskan tidak ada kolom yang cocok dengan kriteria data profil Anda."
                
    except Exception as e:
        return f"❌ Gagal memproses analisis otomatisasi pintar pada situs tersebut. Kendala: `{str(e)}`"

# Handler Perintah /start
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "🤖 *Selamat Datang di Bot Intelijen Airdrop v5 (Kapasitas Besar)!*\n\n"
        "Fitur Utama AI Mandiri:\n"
        "👉 `/isi [URL_SITUS]` - Mengisi data airdrop pintar bebas limit harian kaku.\n\n"
        "🎨 *Gambar:* Ketik `buatkan gambar [deskripsi]`\n"
        "💬 *Chat AI:* Bicara atau perintahkan apa saja, saya akan merespons pintar."
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

# Handler Perintah /isi
async def isi_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ Format salah. Contoh:\n`/isi https://situsairdrop.com/join`", parse_mode="Markdown")
        return
        
    target_url = context.args[0]
    await update.message.reply_text("🧠 *AI sedang mendeteksi & menganalisis secara pintar apa saja yang harus diisi pada situs target...*", parse_mode="Markdown")
    report = await smart_ai_analyze_and_fill(target_url)
    await update.message.reply_text(report, parse_mode="Markdown")

# Handler Utama Chat AI Teks & Gambar
async def handle_ai_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    user_message_lower = user_message.lower()
    
    if user_message_lower.startswith("buatkan gambar") or user_message_lower.startswith("draw"):
        prompt_gambar = user_message.replace("buatkan gambar", "").replace("buatkan Gambar", "").replace("draw", "").replace("Draw", "").strip()
        if not prompt_gambar:
            await update.message.reply_text("⚠️ Masukkan deskripsi gambar.")
            return

        status_msg = await update.message.reply_text("🎨 *Sedang memproses lukisan Anda...*", parse_mode="Markdown")
        try:
            loop = asyncio.get_event_loop()
            def translate_prompt():
                res = ai_client.models.generate_content(model='gemini-1.5-flash', contents=f"Translate to English: {prompt_gambar}")
                return res.text.strip() if res.text else prompt_gambar
            english_prompt = await loop.run_in_executor(None, translate_prompt)
            
            def generate_image():
                return ai_client.models.generate_images(
                    model='imagen-3.0-generate-002',
                    prompt=english_prompt,
                    config=types.GenerateImagesConfig(number_of_images=1, aspect_ratio="1:1", safety_filter_level="BLOCK_LOW_AND_ABOVE")
                )
            result = await loop.run_in_executor(None, generate_image)
            
            if result and result.generated_images:
                for generated_image in result.generated_images:
                    raw_bytes = generated_image.image.image_bytes
                    image_file = io.BytesIO(raw_bytes)
                    image_file.name = 'ai_generation.jpg'
                    await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=status_msg.message_id)
                    await update.message.reply_photo(photo=image_file, caption=f"✨ Hasil kreasi mandiri untuk: *{prompt_gambar}*", parse_mode="Markdown")
                    return
        except Exception as e:
            await update.message.reply_text(f"❌ Gagal memproses gambar: `{str(e)}`")
            return

    # CHAT TEKS BIASA
    system_prompt = f"Anda adalah AI Asisten Crypto Serbabisa yang mandiri dan solutif. Jawab pertanyaan pengguna: {user_message}"
    try:
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: ai_client.models.generate_content(model='gemini-1.5-flash', contents=system_prompt))
        if response and response.text:
            for part in split_message(response.text):
                await update.message.reply_text(part, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"🧠 *Otak AI kendala:* `{str(e)}`")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("isi", isi_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_ai_chat))
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
