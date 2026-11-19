import os
import asyncio
import logging
import sys
from aiohttp import web
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from openai import OpenAI

# Принудительная установка UTF-8
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

groq_client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1"
) if GROQ_API_KEY else None

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

def get_model_keyboard():
    return types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="Llama 3 (Groq)")],
            [types.KeyboardButton(text="Status")]
        ],
        resize_keyboard=True
    )

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.update_data(model="Groq")
    await message.answer(
        "Bot connected to Groq successfully!\nSend any message to test.",
        reply_markup=get_model_keyboard()
    )

@dp.message(F.text == "Llama 3 (Groq)")
async def select_groq(message: types.Message, state: FSMContext):
    await state.update_data(model="Groq")
    await message.answer("Active model: Llama 3 (Groq)")

@dp.message(F.text == "Status")
async def check_status(message: types.Message, state: FSMContext):
    key_status = "Connected" if GROQ_API_KEY else "Missing"
    await message.answer(f"Groq API Key status: {key_status}")

@dp.message(F.text)
async def handle_message(message: types.Message, state: FSMContext):
    if not groq_client:
        await message.answer("Error: GROQ_API_KEY is not set in Render.")
        return

    await bot.send_chat_action(message.chat.id, action="typing")

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": message.text}]
        )
        answer = response.choices[0].message.content

        for i in range(0, len(answer), 4096):
            await message.answer(answer[i:i+4096])

    except Exception as e:
        err_msg = str(e).encode('ascii', 'ignore').decode('ascii')
        await message.answer(f"API Error occurred: {err_msg}")

async def handle_web(request):
    return web.Response(text="Bot is running!")

async def web_server():
    app = web.Application()
    app.router.add_get("/", handle_web)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

async def main():
    await web_server()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
