import os
import re
import logging
import threading
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
import yt_dlp

# --- НАСТРОЙКИ ---
# Токен берем из переменных окружения (на хостинге так безопаснее)
BOT_TOKEN = os.environ.get("8983044387:AAGPxTd_XLeWIFEjyCqZh_96EP50FoQQvtE")
if not BOT_TOKEN:
    raise ValueError("Не задан TELEGRAM_TOKEN в переменных окружения!")

DOWNLOAD_DIR = "downloads"
# ------------------

# Flask приложение для здоровья сервиса
app = Flask(__name__)

@app.route('/')
@app.route('/health')
def health_check():
    return "Bot is running", 200

# Создаем папку для скачивания
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Отправь мне ссылку на видео, и я попробую его скачать."
    )

async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    if not re.match(r'https?://', url):
        await update.message.reply_text("Пожалуйста, отправь корректную ссылку.")
        return

    msg = await update.message.reply_text("⏳ Начинаю загрузку...")

    ydl_opts = {
        'outtmpl': f'{DOWNLOAD_DIR}/%(title)s.%(ext)s',
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'merge_output_format': 'mp4',
        'noplaylist': True,
    }

    filename = None
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

        await msg.edit_text("📤 Загружаю видео в Telegram...")

        with open(filename, 'rb') as video_file:
            await update.message.reply_video(video=video_file)

        os.remove(filename)
        await msg.delete()

    except Exception as e:
        logging.error(f"Ошибка: {e}")
        await msg.edit_text(f"❌ Ошибка: {str(e)[:200]}")
        if filename and os.path.exists(filename):
            os.remove(filename)

def run_bot():
    """Запускает Telegram бота в отдельном потоке"""
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(MessageHandler(filters.Regex(r'^/start'), start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_video))
    print("Бот запущен...")
    application.run_polling()

if __name__ == '__main__':
    # Запускаем бота в фоне
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()

    # Запускаем Flask для хостинга
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
