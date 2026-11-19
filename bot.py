import os
import asyncio
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from openai import OpenAI

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Инициализация клиента Groq с базовым URL Groq API
groq_client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1"
) if GROQ_API_KEY else None

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

def get_model_keyboard():
    return types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="⚡ Llama 3 (Groq)")],
            [types.KeyboardButton(text="⚙️ Статус системы")]
        ],
        resize_keyboard=True
    )

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.update_data(model="Groq Llama 3")
    await message.answer(
        "Связка с <b>Groq (Llama 3)</b> запущена!\n"
        "Отправь любой вопрос в чат для проверки.",
        parse_mode="HTML",
        reply_markup=get_model_keyboard()
    )

@dp.message(F.text == "⚡ Llama 3 (Groq)")
async def select_groq(message: types.Message, state: FSMContext):
    await state.update_data(model="Groq Llama 3")
    await message.answer("✅ Активная модель: <b>Llama 3 (Free Groq)</b>", parse_mode="HTML")

@dp.message(F.text == "⚙️ Статус системы")
async def check_status(message: types.Message, state: FSMContext):
    data = await state.get_data()
    current = data.get("model", "Groq Llama 3")
    status_text = (
        f"Текущая модель: <b>{current}</b>\n"
        f"Ключ Groq: {'🟢 Подключен' if GROQ_API_KEY else '🔴 Отсутствует'}"
    )
    await message.answer(status_text, parse_mode="HTML")

@dp.message(F.text)
async def handle_message(message: types.Message, state: FSMContext):
    if not groq_client:
        await message.answer("❌ Ключ GROQ_API_KEY не найден в настройках Render.")
        return

    await bot.send_chat_action(message.chat.id, action="typing")

    try:
        # Запрос к быстрой и бесплатной модели llama-3.3-70b-versatile (или llama3-8b)
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": message.text}]
        )
        answer = response.choices[0].message.content

        for i in range(0, len(answer), 4096):
            await message.answer(answer[i:i+4096])

    except Exception as e:
        logging.error(f"Ошибка Groq: {e}")
        await message.answer(f"⚠️ Ошибка при обращении к Groq:\n<code>{str(e)}</code>", parse_mode="HTML")

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
