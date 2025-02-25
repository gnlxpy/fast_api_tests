import smtplib
import os
import traceback

from dotenv import load_dotenv
from email.message import EmailMessage


load_dotenv()

EMAIL_USER=os.getenv('EMAIL_USER')
EMAIL_PSW=os.getenv('EMAIL_PSW')


def send_email(recipient: str, subject: str, message_body: str) -> bool:
    """
    Отправка емейл
    :param recipient: емейл адресата
    :param subject: тема
    :param message_body: тело сообщения
    :return: True | False
    """
    try:
        # инициализация соединения с сервером
        server = smtplib.SMTP('smtp.yandex.ru', 587)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PSW)

        # создание сообщения
        msg = EmailMessage()
        msg.set_content(message_body)
        msg["Subject"] = subject
        msg["From"] = EMAIL_USER
        msg["To"] = recipient

        # отправка и закрытие соединения
        server.send_message(msg)
        server.close()
        return True
    except Exception:
        return False
