import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# Вставь сюда свой токен, который получил у @BotFather
API_TOKEN = '8024802229:AAHEknWnyIkcCRVBufuyKvZK68n0MUvJKtQ'

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Обработка команды /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Привет! Я твой бот, запущенный на хостинге. Отправь мне любое сообщение!")

# Эхо-режим: бот повторяет присланный текст
@dp.message()
async def echo_handler(message: types.Message):
    try:
        # Отправляем копию полученного сообщения
        await message.send_copy(chat_id=message.chat.id)
    except TypeError:
        # Если тип сообщения не поддерживается (например, стикер)
        await message.answer("Я пока умею повторять только текст!")

async def main():
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
