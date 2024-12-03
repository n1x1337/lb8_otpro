import asyncio
import os
import re
import logging
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, Router
from aiogram.types import Message
from aiogram.filters import Command
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
import ssl

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = os.getenv("SMTP_PORT", 465)
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
router = Router()

user_data = {}

def is_valid_email(email):
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return re.match(pattern, email)

def send_email(to_email, message_body):
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=context) as server:
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        msg = MIMEMultipart()
        msg["From"] = SMTP_USERNAME
        msg["To"] = to_email
        msg["Subject"] = "Тестовое сообщение для лабораторной работы"
        msg.attach(MIMEText(message_body, "plain"))
        server.send_message(msg)

@router.message(Command(commands=["start"]))
async def start_handler(message: Message):
    user_data[message.chat.id] = {"is_sent": False, "waiting_for_email": True}
    await message.answer("Введите email куда посылаем сообщение:")

@router.message(lambda message: message.chat.id in user_data and user_data[message.chat.id]["waiting_for_email"])
async def email_handler(message: Message):
    if message.text.strip().upper() == "СТОП":
        if user_data[message.chat.id].get("is_sent", False):
            user_data.pop(message.chat.id, None)
            await message.answer("Работа завершена. До свидания!")
        else:
            await message.answer("Вы не можете использовать СТОП, пока не отправите хотя бы одно сообщение.")
        return

    email = message.text.strip()
    if is_valid_email(email):
        user_data[message.chat.id]["email"] = email
        user_data[message.chat.id]["waiting_for_email"] = False
        await message.answer("Введите само сообщение:")
    else:
        await message.answer("Некорректный email. Попробуйте снова:")

@router.message(lambda message: message.chat.id in user_data and not user_data[message.chat.id]["waiting_for_email"])
async def message_handler(message: Message):
    if message.text.strip().upper() == "СТОП":
        if user_data[message.chat.id]["is_sent"]:
            user_data.pop(message.chat.id, None)
            await message.answer("Работа завершена. До свидания!")
        else:
            await message.answer("Вы не можете использовать СТОП, пока не отправите хотя бы одно сообщение.")
        return

    user_message = message.text.strip()
    user_email = user_data[message.chat.id]["email"]
    try:
        send_email(user_email, user_message)
        user_data[message.chat.id]["is_sent"] = True
        user_data[message.chat.id]["waiting_for_email"] = True
        await message.answer("Сообщение успешно отправлено! Хотите отправить еще одно сообщение? Введите новый email, или напишите СТОП для завершения работы:")
    except Exception as e:
        logging.error(f"Ошибка при отправке сообщения: {e}")
        await message.answer("Произошла ошибка при отправке сообщения. Пожалуйста, введите email заново:")

async def main():
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
