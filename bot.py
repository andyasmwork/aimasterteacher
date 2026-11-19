import os
import asyncio
import logging
import sys
import re
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from aiohttp import web
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from openai import OpenAI

from config import AI_MODEL, PORT, SMTP_SERVER, SMTP_PORT, SMTP_USER, SMTP_PASSWORD
from database import get_student, save_student_field, add_progress_record

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

# Определяем состояния регистрации (FSM)
class RegistrationStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_email = State()
    waiting_for_code = State()

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

def send_email_code(to_email, code):
    """Отправка кода подтверждения на email через SMTP"""
    if not SMTP_USER or not SMTP_PASSWORD:
        logging.warning("SMTP credentials not set. Code simulation: " + str(code))
        return True # Для теста без настроенной почты
    
    try:
        msg = MIMEMultipart()
        msg['From'] = SMTP_USER
        msg['To'] = to_email
        msg['Subject'] = "Подтверждение регистрации | Элизабет 3.0"
        
        body = f"Здравствуйте!\n\nВаш код подтверждения для доступа к обучению: {code}\n\nЕсли вы не запрашивали этот код, просто проигнорируйте письмо."
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_USER, to_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        logging.error(f"SMTP Error: {e}")
        return False

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    student = get_student(user_id)
    
    if student and student.get("email_verified"):
        await message.answer("С возвращением! Вы уже зарегистрированы и можете продолжать обучение.")
        return

    await state.set_state(RegistrationStates.waiting_for_name)
    await message.answer(
        "👋 Привет! Я **Элизабет 3.0** — твой персональный преподаватель и практический наставник по ИИ.\n\n"
        "Для начала обучения нам нужно завести твой профиль. Как тебя зовут? (Укажи Имя и Фамилию)"
    )

@dp.message(RegistrationStates.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    save_student_field(message.from_user.id, "name", message.text.strip())
    await state.set_state(RegistrationStates.waiting_for_phone)
    await message.answer("Отлично! Теперь укажи свой номер телефона для связи:")

@dp.message(RegistrationStates.waiting_for_phone)
async def process_phone(message: types.Message, state: FSMContext):
    save_student_field(message.from_user.id, "phone", message.text.strip())
    await state.set_state(RegistrationStates.waiting_for_email)
    await message.answer("Принято! Теперь укажи свой действующий **Email** (на него придет код подтверждения):")

@dp.message(RegistrationStates.waiting_for_email)
async def process_email(message: types.Message, state: FSMContext):
    email = message.text.strip()
    if "@" not in email or "." not in email:
        await message.answer("⚠️ Похоже, это некорректный email. Пожалуйста, введи действующий адрес:")
        return
    
    code = str(random.randint(100000, 999999))
    save_student_field(message.from_user.id, "email", email)
    save_student_field(message.from_user.id, "verification_code", code)
    
    success = send_email_code(email, code)
    
    if success:
        await state.set_state(RegistrationStates.waiting_for_code)
        await message.answer(
            f"📨 Мы отправили 6-значный код подтверждения на почту: <code>{email}</code>\n\n"
            "Пожалуйста, проверьте входящие сообщения.\n"
            "⚠️ <i>Если письма нет долго, обязательно проверьте папку **«Спам»** или **«Нежелательная почта»**!</i>\n\n"
            "Введите полученный код:",
            parse_mode="HTML"
        )
    else:
        await message.answer("⚠️ Не удалось отправить письмо на этот адрес. Пожалуйста, проверьте правильность и введите email еще раз:")

@dp.message(RegistrationStates.waiting_for_code)
async def process_code(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    student = get_student(user_id)
    user_code = message.text.strip()
    
    if student and user_code == str(student.get("verification_code")):
        save_student_field(user_id, "email_verified", True)
        await state.clear()
        await message.answer(
            "✅ **Почта успешно подтверждена!** Регистрация завершена.\n\n"
            "Теперь вы можете полноценно приступить к программе обучения. Отправьте любое сообщение, чтобы начать первое занятие!",
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "❌ Неверный код подтверждения.\n"
            "Пожалуйста, проверьте почту (включая папку **Спам**) и введите правильный код еще раз:"
        )

# Основной обработчик сообщений для зарегистрированных учеников
@dp.message(F.text)
async def handle_message(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    student = get_student(user_id)
    
    # Если ученик не зарегистрирован или не подтвердил email — блокируем доступ дальше
    if not student or not student.get("email_verified"):
        await message.answer("⚠️ Пожалуйста, завершите регистрацию и подтвердите вашу почту, прежде чем продолжать обучение. Введите /start")
        return

    if not client:
        await message.answer("Error: OPENROUTER_API_KEY is not set in Render.")
        return

    await bot.send_chat_action(message.chat.id, action="typing")

    try:
        response = client.chat.completions.create(
            model=AI_MODEL,
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
    server_port = int(os.environ.get("PORT", PORT))
    site = web.TCPSite(runner, "0.0.0.0", server_port)
    await site.start()

async def main():
    await web_server()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
