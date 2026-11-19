import os
import asyncio
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from google import genai

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Инициализация клиента Google GenAI
client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

def get_model_keyboard():
    return types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="✨ Gemini Free")],
            [types.KeyboardButton(text="⚙️ Статус системы")]
        ],
        resize_keyboard=True
    )

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.update_data(model="Gemini")
    await message.answer(
        "Связка с <b>Google Gemini</b> запущена!\n"
        "Отправь любой вопрос в чат для проверки.",
        parse_mode="HTML",
        reply_markup=get_model_keyboard()
    )

@dp.message(F.text == "✨ Gemini Free")
async def select_gemini(message: types.Message, state: FSMContext):
    await state.update_data(model="Gemini")
    await message.answer("✅ Активная модель: <b>Google Gemini (Free)</b>", parse_mode="HTML")

@dp.message(F.text == "⚙️ Статус системы")
async def check_status(message: types.Message, state: FSMContext):
    data = await state.get_data()
    current = data.get("model", "Gemini")
    status_text = (
        f"Текущая модель: <b>{current}</b>\n"
        f"Ключ Gemini: {'🟢 Подключен' if GEMINI_API_KEY else '🔴 Отсутствует'}"
    )
    await message.answer(status_text, parse_mode="HTML")

@dp.message(F.text)
async def handle_message(message: types.Message, state: FSMContext):
    if not client:
        await message.answer("❌ Ключ GEMINI_API_KEY не найден в настройках Render.")
        return

    await bot.send_chat_action(message.chat.id, action="typing")

    try:
        # Запрос к бесплатной быстрой модели gemini-2.5-flash
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=message.text,
        )
        answer = response.text

        for i in range(0, len(answer), 4096):
            await message.answer(answer[i:i+4096])

    except Exception as e:
        logging.error(f"Ошибка Gemini: {e}")
        await message.answer(f"⚠️ Ошибка при обращении к Gemini:\n<code>{str(e)}</code>", parse_mode="HTML")

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
