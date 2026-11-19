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
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

deepseek_client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com"
) if DEEPSEEK_API_KEY else None

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

def get_model_keyboard():
    return types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="🚀 DeepSeek")],
            [types.KeyboardButton(text="⚙️ Статус системы")]
        ],
        resize_keyboard=True
    )

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.update_data(model="DeepSeek")
    await message.answer(
        "Связка запущена! Активная модель: <b>DeepSeek</b>.\n"
        "Отправь любой вопрос в чат для проверки.",
        parse_mode="HTML",
        reply_markup=get_model_keyboard()
    )

@dp.message(F.text == "🚀 DeepSeek")
async def select_deepseek(message: types.Message, state: FSMContext):
    await state.update_data(model="DeepSeek")
    await message.answer("✅ Выбрана модель: <b>DeepSeek</b>", parse_mode="HTML")

@dp.message(F.text == "⚙️ Статус системы")
async def check_status(message: types.Message, state: FSMContext):
    data = await state.get_data()
    current = data.get("model", "DeepSeek")
    status_text = (
        f"Текущая модель: <b>{current}</b>\n"
        f"Ключ DeepSeek: {'🟢 Подключен' if DEEPSEEK_API_KEY else '🔴 Отсутствует'}"
    )
    await message.answer(status_text, parse_mode="HTML")

@dp.message(F.text)
async def handle_message(message: types.Message, state: FSMContext):
    if not deepseek_client:
        await message.answer("❌ Ключ DEEPSEEK_API_KEY не найден в настройках Render.")
        return

    await bot.send_chat_action(message.chat.id, action="typing")

    try:
        response = deepseek_client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": message.text}]
        )
        answer = response.choices[0].message.content

        for i in range(0, len(answer), 4096):
            await message.answer(answer[i:i+4096])

    except Exception as e:
        logging.error(f"Ошибка DeepSeek: {e}")
        await message.answer(f"⚠️ Ошибка при обращении к DeepSeek:\n<code>{str(e)}</code>", parse_mode="HTML")

# Веб-сервер для удержания бесплатного порта Render
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

