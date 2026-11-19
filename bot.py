import os
import asyncio
import logging
import sys
import re
from aiohttp import web
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from openai import OpenAI

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

client = OpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1"
) if OPENROUTER_API_KEY else None

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Функция для чтения инструкции из внешнего файла
def load_instruction():
    filename = "instruction.txt"
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            logging.error(f"Error reading instruction file: {e}")
    return "Ты — Элизабет 3.0, персональный наставник по искусственному интеллекту."

SYSTEM_INSTRUCTION = load_instruction()

# Обработчик служебной команды для проверки версии инструкции
@dp.message(Command("aiminstruction"))
async def cmd_aiminstruction(message: types.Message):
    # Извлекаем версию из первой строки файла по тегу
    version_match = re.search(r"\[INSTRUCTION_VERSION:\s*(.*?)\]", SYSTEM_INSTRUCTION)
    version_info = version_match.group(1) if version_match else "Версия не указана"
    
    await message.answer(
        f"📋 **Статус инструкции Элизабет:**\n"
        f"• Файл: <code>instruction.txt</code>\n"
        f"• Параметр версии: <b>{version_info}</b>\n"
        f"• Статус: Успешно загружена в память бота.",
        parse_mode="HTML"
    )

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.update_data(model="OpenRouter")
    
    try:
        response = client.chat.completions.create(
            model="meta-llama/llama-3.1-8b-instruct:free",
            messages=[
                {"role": "system", "content": SYSTEM_INSTRUCTION},
                {"role": "user", "content": "Привет! Я готов начать обучение. Представься и задай первый вопрос диагностики."}
            ]
        )
        answer = response.choices[0].message.content
        await message.answer(answer)
    except Exception as e:
        await message.answer("Привет! Я Элизабет 3.0 — твой наставник по ИИ. Напиши любое сообщение, чтобы начать!")

@dp.message(F.text)
async def handle_message(message: types.Message, state: FSMContext):
    if not client:
        await message.answer("Error: OPENROUTER_API_KEY is not set in Render.")
        return

    await bot.send_chat_action(message.chat.id, action="typing")

    try:
        response = client.chat.completions.create(
            model="meta-llama/llama-3.1-8b-instruct:free",
            messages=[
                {"role": "system", "content": SYSTEM_INSTRUCTION},
                {"role": "user", "content": message.text}
            ]
        )
        answer = response.choices[0].message.content

        for i in range(0, len(answer), 4096):
            await message.answer(answer[i:i+4096])

    except Exception as e:
        error_text = str(e).encode('ascii', 'ignore').decode('ascii')
        await message.answer(f"API Error: {error_text[:200]}")

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
