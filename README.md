# To-Do mini

## Описание
Тестовый проект FastAPI для backend to-do менеджера задач.

## Структура проекта
```
fast_api_tests.py/
|-- main.py                # основной код приложения FastAPI
|-- static/                # вспомогательные файлы для web
|-- templates/             # шаблоны страниц для web
|   |-- index.html         # страница входа
|   |-- login.html         # авторизация
|   |-- me.html            # страница ЛК
|   |-- registration.html  # регистрация
|   |-- verified.html      # страница подтверждения почты
|-- models.py              # Pydantic-модели для FastAPI
|-- encryption.py          # вспомогательные функции проекта по шифрованию (jwt, CryptContext)
|-- redis_handler.py       # хранилище Redis (redis.asyncio)
|-- s3_handler.py          # работа с AWS s3 (aioboto3)
|-- sql.py                 # БД Postgresql на чистом SQL (asyncpg)
|-- tasks.py               # очередь задач (Celery)
|-- email_handler.py       # вспомогательные функции проекта по отправке почты (smtplib)
|-- tests/                 # тестирование с pytest
|   |-- unit/              # юнит-тесты
```
