import subprocess
from contextlib import asynccontextmanager
from routers import lk, task
import redis.asyncio as redis
import uvicorn
from fastapi import FastAPI, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi_limiter import FastAPILimiter
from models import FormValidationError
from routers.lk import templates
from config import settings


@asynccontextmanager
async def lifespan(_: FastAPI):
    """
    Инициализация Редис для fastapi_limiter
    """
    redis_connection = redis.from_url(settings.REDIS_URL, encoding="utf8")
    await FastAPILimiter.init(redis_connection)
    yield
    await FastAPILimiter.close()


# инициализация фастапи
app = FastAPI(lifespan=lifespan, title='To-Do mini', description='Позволяет хранить задачи в облаке. Для регистрации пройдите по ссылке: /registration', version='0.1b')
# Подключение к статическим файлам (например, Bootstrap и стили)
app.mount('/static', StaticFiles(directory='static'), name='static')
# подключение роутеров
app.include_router(lk.router)
app.include_router(task.router)


@app.middleware("http")
async def check_session_middleware(request: Request, call_next):
    """
    Обработчик запросов в ЛК
    """
    if request.url.path in ['/lk', '/lk/login', '/lk/registration']:
        user_session = request.cookies.get("user_session")
        if user_session:
            return RedirectResponse(url='/lk/me', status_code=303)
    response = await call_next(request)
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Обработчик стандартных ошибок при регистрации
    """
    ctx = exc.errors()[0].get('ctx')
    if ctx and isinstance(ctx.get('error'), FormValidationError):
        return templates.TemplateResponse('registration.html',
                                          {'request': request, 'message': exc.errors()[0]['msg'].replace('Value error, ', '')})
    else:
        return await request_validation_exception_handler(request, exc)


@app.get('/', response_class=HTMLResponse, tags=['account'])
async def index():
    """
    ## Главная страница
    Содержит кнопку регистрация и логин
    """
    return RedirectResponse(url='/lk', status_code=303)


if __name__ == "__main__":
    celery_process = subprocess.Popen(
        ["celery", "-A", "tasks", "worker", "--loglevel=info"]
    )
    try:
        uvicorn.run("main:app", reload=True, use_colors=True, workers=4)
    finally:
        celery_process.terminate()
