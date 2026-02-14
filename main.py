import os
import logging
import tempfile
import speech_recognition as sr
from pydub import AudioSegment
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Токен бота (НЕ ДЕЛИТЕСЬ ИМ НИ С КЕМ!)
BOT_TOKEN = "8024802229:AAHEknWnyIkcCRVBufuyKvZK68n0MUvJKtQ"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    await update.message.reply_text(
        "👋 Привет! Я бот для расшифровки голосовых сообщений.\n\n"
        "Просто отправь мне голосовое сообщение, и я пришлю его текстовую расшифровку.\n"
        "Поддерживаются голосовые сообщения Telegram и аудиофайлы."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    await update.message.reply_text(
        "📝 Как пользоваться ботом:\n\n"
        "1. Отправь мне голосовое сообщение\n"
        "2. Подожди несколько секунд\n"
        "3. Получи текст расшифровки\n\n"
        "⚠️ Расшифровка может быть не идеальной, если запись с шумами."
    )

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик голосовых сообщений"""
    temp_files = []
    
    try:
        # Отправляем статус обработки
        status_message = await update.message.reply_text("🔄 Обрабатываю голосовое сообщение...")
        
        # Получаем файл голосового сообщения
        voice = update.message.voice
        file = await context.bot.get_file(voice.file_id)
        
        # Создаем временные файлы
        with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as ogg_file:
            ogg_path = ogg_file.name
            temp_files.append(ogg_path)
        
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as wav_file:
            wav_path = wav_file.name
            temp_files.append(wav_path)
        
        # Скачиваем голосовое сообщение
        await file.download_to_drive(ogg_path)
        logger.info(f"Файл скачан: {ogg_path}")
        
        # Обновляем статус
        await status_message.edit_text("🔄 Конвертирую аудио...")
        
        # Конвертируем OGG в WAV
        try:
            audio = AudioSegment.from_file(ogg_path, format="ogg")
            audio = audio.set_frame_rate(16000).set_channels(1)
            audio.export(wav_path, format="wav")
            logger.info(f"Файл сконвертирован: {wav_path}")
        except Exception as e:
            logger.error(f"Ошибка конвертации: {e}")
            await status_message.edit_text("❌ Ошибка при обработке аудиофайла. Убедитесь, что на сервере установлен FFmpeg.")
            return
        
        # Обновляем статус
        await status_message.edit_text("🔄 Распознаю речь...")
        
        # Распознаем речь
        recognizer = sr.Recognizer()
        
        try:
            with sr.AudioFile(wav_path) as source:
                # Настройка на уровень шума
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio_data = recognizer.record(source)
                
                # Пробуем распознать на русском
                try:
                    text = recognizer.recognize_google(audio_data, language="ru-RU")
                    result_text = f"📝 **Распознанный текст:**\n\n{text}"
                except:
                    # Если не получилось на русском, пробуем на английском
                    try:
                        text = recognizer.recognize_google(audio_data, language="en-US")
                        result_text = f"📝 **Recognized text (English):**\n\n{text}"
                    except sr.UnknownValueError:
                        result_text = "❌ Не удалось распознать речь. Возможно, запись слишком тихая или неразборчивая."
                    except sr.RequestError:
                        result_text = "❌ Ошибка подключения к сервису распознавания."
                        
        except Exception as e:
            logger.error(f"Ошибка распознавания: {e}")
            result_text = f"❌ Ошибка при распознавании: {str(e)}"
        
        # Отправляем результат
        await status_message.edit_text(result_text)
        
    except Exception as e:
        logger.error(f"Общая ошибка: {e}")
        await update.message.reply_text(f"❌ Произошла ошибка: {str(e)}")
    
    finally:
        # Очищаем временные файлы
        for file_path in temp_files:
            try:
                if os.path.exists(file_path):
                    os.unlink(file_path)
                    logger.info(f"Удален временный файл: {file_path}")
            except Exception as e:
                logger.error(f"Ошибка при удалении {file_path}: {e}")

def main():
    """Запуск бота"""
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    
    # Добавляем обработчик голосовых сообщений
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))
    
    # Запускаем бота
    logger.info("Бот запущен и готов к работе!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
