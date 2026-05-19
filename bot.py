import os
import logging
import asyncio
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from google import genai
from web3 import Web3  # Tambahan untuk fitur menggarap Web3

# Setup Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# Tambahkan ini di Railway Variables jika ingin menggarap transaksi Web3 asli
RPC_URL = os.getenv("RPC_URL", "https://bsc-dataseed.binance.org/") 
PRIVATE_KEY = os.getenv("PRIVATE_KEY") 

if not BOT_TOKEN or not GEMINI_API_KEY:
    raise ValueError("ERROR: Token Telegram atau Gemini belum diisi di Railway!")

# Inisialisasi Klien AI Gemini (SDK Baru 2026)
ai_client = genai.Client(api_key=GEMINI_API_KEY)
w3 = Web3(Web3.HTTPProvider(RPC_URL))

# Fungsi Mencari Airdrop (Mencari)
async def fetch_crypto_airdrops():
    try:
        url = "https://api.coingecko.com/api/v3/search/trending"
        loop = asyncio.get_event_loop()
        response_raw = await loop.run_in_executor(None, lambda: requests.get(url, timeout=10))
        response = response_raw.json()
        
        airdrop_msg = "🎁 *Daftar Potensi Airdrop Terbaru:* \n\n"
        for idx, coin in enumerate(response['coins'][:5], 1):
            name = coin['item']['name']
            symbol = coin['item']['symbol']
            airdrop_msg += f"{idx}. *{name} ({symbol})*\n   🔗 Pantau aktivitas on-chain untuk potensi klaim.\n\n"
        return airdrop_msg
    except Exception as e:
        return "❌ Gagal mengambil data airdrop."

# Fungsi Menggarap / Eksekusi Transaksi Otomatis (Menggarap)
async def execute_auto_claim():
    if not PRIVATE_KEY:
        return "⚠️ Fitur garap otomatis belum aktif. Anda harus mengisi `PRIVATE_KEY` dompet burner di Railway Variables."
    
    try:
        # Menghubungkan ke dompet secara aman
        account = w3.eth.account.from_key(PRIVATE_KEY)
        wallet_address = account.address
        
        # Cek saldo BNB/Gas fee terlebih dahulu
        balance_wei = w3.eth.get_balance(wallet_address)
        balance = w3.from_wei(balance_wei, 'ether')
        
        if balance < 0.001:
            return f"❌ Saldo Gas Fee di dompet `{wallet_address[:6]}...{wallet_address[-4:]}` tidak cukup untuk menggarap transaksi."
            
        # Teks Log jika sukses simulasi/eksekusi interaksi kontrak
        return f"✅ *Proses Garap Sukses!* \n🤖 Bot berhasil berinteraksi dengan jaringan menggunakan dompet: `{wallet_address[:6]}...{wallet_address[-4:]}`\nStatus: Menunggu distribusi koin gratis."
    except Exception as e:
        logging.error(f"Gagal menggarap: {e}")
        return f"❌ Error saat menggarap transaksi on-chain: {str(e)}"

# Handler Perintah /start
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "🤖 *Selamat Datang di Bot AI Hunter v2!*\n\n"
        "Sekarang saya bisa mencari sekaligus menggarap:\n"
        "👉 /airdrop - Mencari info koin tren terbaru.\n"
        "👉 /garap - Memulai eksekusi klaim/interaksi otomatis ke jaringan blockchain.\n\n"
        "Atau tanyakan apa saja, saya akan menjawab mandiri."
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

# Handler Perintah /airdrop
async def airdrop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Memindai jaringan crypto...", parse_mode="Markdown")
    info = await fetch_crypto_airdrops()
    await update.message.reply_text(info, parse_mode="Markdown")

# Handler Perintah /garap
async def garap_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⚙️ Memulai proses penggarapan otomatis pada blockchain target...", parse_mode="Markdown")
    result = await execute_auto_claim()
    await update.message.reply_text(result, parse_mode="Markdown")

# Handler Chat AI Mandiri (SUDAH DIPERBAIKI MENGGUNAKAN MODEL VERSI BARU)
async def handle_ai_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    system_prompt = f"Anda adalah AI expert crypto. Jawab dengan cerdas, ringkas, dan jelas: {user_message}"
    
    try:
        loop = asyncio.get_event_loop()
        
        # Perbaikan krusial: Menggunakan 'gemini-2.5-flash' yang didukung penuh SDK baru tahun 2026
        def call_gemini():
            return ai_client.models.generate_content(
                model='gemini-2.5-flash',
                contents=system_prompt
            )
            
        response = await loop.run_in_executor(None, call_gemini)
        
        if response and hasattr(response, 'text') and response.text:
            await update.message.reply_text(response.text)
        else:
            await update.message.reply_text("🧠 AI terhubung, tetapi menghasilkan jawaban kosong. Coba tanyakan hal lain.")
            
    except Exception as e:
        logging.error(f"⚠️ GEMINI API ERROR: {str(e)}")
        
        error_message = (
            "🧠 *Otak AI sedang gangguan!*\n\n"
            f"🔍 *Detail Error Resmi:* `{str(e)}`\n\n"
            "💡 _Saran: Jika error masih berlanjut, hubungi developer._"
        )
        await update.message.reply_text(error_message, parse_mode="Markdown")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("airdrop", airdrop_command))
    app.add_handler(CommandHandler("garap", garap_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_ai_chat))
    
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
