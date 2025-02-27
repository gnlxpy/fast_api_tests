from celery import Celery
from email_handler import send_email
from config import settings


# Конфигурация Celery
celery_app = Celery('tasks', broker=settings.REDIS_URL, encoding="utf8")

@celery_app.task
def send_email_task(recipient: str, username: str, url_confirm: str) -> bool:
    send_status = send_email(recipient,
                             'Подтверждение электронной почты - To-Do micro-api',
                             f'Здравствуйте, {username}\n'
                             f'Для подтверждения своей почты в сервисе To-Do micro-api перейдите по ссылке ниже:\n'
                             f'{url_confirm}'
                             )
    return send_status
