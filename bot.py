import os
import subprocess
from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import ContentType

# Берем токен из настроек сервера (переменная окружения)
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise SystemExit("ОШИБКА: Не задан BOT_TOKEN в настройках сервера!")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

@dp.message_handler(content_types=ContentType.VIDEO)
async def handle_video(message: types.Message):
    await message.reply("⏳ Обрабатываю видео...")
    try:
        file = await bot.get_file(message.video.file_id)
        input_path = f"input_{message.video.file_id}.mp4"
        await bot.download_file(file.file_path, input_path)

        output_path = f"output_{message.video.file_id}.mp4"

        cmd = [
            "ffmpeg", "-y",
            "-i", input_path,
            "-t", "59",
            "-vf", "crop=ih:ih,scale=640:640,setsar=1",
            "-c:v", "libx264",
            "-c:a", "aac",
            "-preset", "ultrafast",
            output_path
        ]
        subprocess.run(cmd, check=True, capture_output=True)

        with open(output_path, "rb") as video:
            await message.reply_video_note(video)

    except FileNotFoundError:
        await message.reply("❌ FFmpeg не установлен на сервере.")
    except subprocess.CalledProcessError as e:
        await message.reply(f"❌ Ошибка обработки видео.")
    except Exception as e:
        await message.reply(f"❌ Ошибка: {e}")
    finally:
        if os.path.exists(input_path): os.remove(input_path)
        if os.path.exists(output_path): os.remove(output_path)

@dp.message_handler(content_types=ContentType.PHOTO)
async def handle_photo(message: types.Message):
    await message.reply("⏳ Делаю кружок из фото...")
    try:
        photo = message.photo[-1]
        file = await bot.get_file(photo.file_id)
        input_path = f"input_{photo.file_id}.jpg"
        await bot.download_file(file.file_path, input_path)

        output_path = f"output_{photo.file_id}.mp4"

        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", input_path,
            "-t", "2",
            "-vf", "crop=ih:ih,scale=640:640,setsar=1",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-preset", "ultrafast",
            output_path
        ]
        subprocess.run(cmd, check=True, capture_output=True)

        with open(output_path, "rb") as video:
            await message.reply_video_note(video)

    except FileNotFoundError:
        await message.reply("❌ FFmpeg не установлен на сервере.")
    except subprocess.CalledProcessError as e:
        await message.reply(f"❌ Ошибка обработки фото.")
    except Exception as e:
        await message.reply(f"❌ Ошибка: {e}")
    finally:
        if os.path.exists(input_path): os.remove(input_path)
        if os.path.exists(output_path): os.remove(output_path)

@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message):
    await message.reply("👋 Отправь мне видео или фото — я сделаю из него кружок.")

if __name__ == "__main__":
    print("Бот запускается...")
    executor.start_polling(dp, skip_updates=True)
