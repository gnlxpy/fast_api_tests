import os
import subprocess
from contextlib import asynccontextmanager
from datetime import timedelta
from typing import Optional
import redis.asyncio as redis
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Form, Depends, Cookie, HTTPException, Request, Body, Path, status as fastapi_status, \
    UploadFile
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import OAuth2PasswordBearer
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
from starlette.responses import JSONResponse
from encryption import create_access_token, hash_password, verify_password, check_token
from models import TaskAdd, Login, Registration, Answer, FormValidationError
from sql import PgActions, HOST
from tasks import send_email_task


SERVER_URL = 'http://127.0.0.1:8000/'
ACCESS_TOKEN_EXPIRE_DAYS = 120
ACCESS_COOKIE_EXPIRE_DAYS = 30
load_dotenv()
REDIS_PSW = os.getenv('REDIS_PSW')

@asynccontextmanager
async def lifespan(_: FastAPI):
    """
    Инициализация Редис для fastapi_limiter
    """
    redis_connection = redis.from_url(f"redis://default:{REDIS_PSW}@{HOST}:6379/db", encoding="utf8")
    await FastAPILimiter.init(redis_connection)
    yield
    await FastAPILimiter.close()


# инициализация фастапи
app = FastAPI(lifespan=lifespan, title='To-Do micro-api', description='Позволяет хранить задачи в облаке. Для регистрации пройдите по ссылке: /registration', version='0.1b')
# Подключение к статическим файлам (например, Bootstrap и стили)
app.mount('/static', StaticFiles(directory='static'), name='static')
# Извлечение токена из запросов
oauth2_scheme = OAuth2PasswordBearer(tokenUrl='token')
# объект бд постгрес
pg = PgActions()
# Подключение к папке с шаблонами
templates = Jinja2Templates(directory='templates')


async def get_user_from_token(request: Request, token: str = Depends(oauth2_scheme)) -> dict | bool:
    """
    Получаем пользователя из токена и проверяем его.
    """
    user = await check_token(token, 'bearer', request.client.host, '/task')
    if not user:
        raise HTTPException(status_code=fastapi_status.HTTP_403_FORBIDDEN, detail="Неверный токен или несуществующий пользователь")
    return user


@app.exception_handler(429)
async def custom_rate_limit_error(request: Request, exc):
    """
    Обработчик ошибок частых запросов
    """
    return JSONResponse(
        status_code=fastapi_status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "detail": "Вы сделали слишком много запросов. Повторите свою попытку позже"
        }
    )


@app.middleware("http")
async def check_session_middleware(request: Request, call_next):
    """
    Обработчик запросов в ЛК
    """
    if request.url.path in ['/', '/login', '/registration']:
        user_session = request.cookies.get("user_session")
        if user_session:
            return RedirectResponse(url='/me', status_code=303)
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
async def index(request: Request):
    """
    ## Главная страница
    Содержит кнопку регистрация и логин
    """
    return templates.TemplateResponse('index.html', {'request': request})


@app.get('/registration', response_class=HTMLResponse, tags=['account'])
async def registration(request: Request):
    """
    ## Страница регистрации пользователя
    Содержит форму с Именем, емейлом, паролем
    """
    return templates.TemplateResponse('registration.html', {'request': request, 'message': None})


@app.post('/registration', tags=['account'])
async def handle_registration(request: Request, form: Registration = Form()):
    """
    ## Обработка присланной формы на странице регистрации
    Проверка повтора пароля и наличия емейл в бд
    Создается токен пользователя для апи
    Пользователь добавляется в бд
    Редирект на страницу логина
    """
    # проверяем существующих пользователей
    user = await pg.users.get(form.email)
    if user is not False:
        return templates.TemplateResponse('registration.html', {'request': request, 'message': 'Пользователь уже существует'})
    # создаем хэш пароля и токен пользователя
    password_hashed = hash_password(form.password)
    access_token = create_access_token(
        form.email, 'bearer', expires_delta=timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    )
    confirm_token = create_access_token(
        form.email, 'confirm', expires_delta=timedelta(days=1)
    )
    send_email_task.delay(form.email, form.username, f'{SERVER_URL}confirm/{confirm_token}')
    # добавляем пользователя в бд
    await pg.users.add(form, password_hashed, access_token)
    # переадресовываем для первого входа в ЛК
    return templates.TemplateResponse('login.html', {'request': request,
                                                     'message': 'Регистрация прошла успешно, войдите для продолжения.'})


@app.get('/confirm/{confirm_code}', include_in_schema=False)
async def confirmation_email(request: Request, confirm_code: str = Path()):
    user = await check_token(confirm_code, 'confirm', request.client.host, '/confirm')
    if user:
        await pg.users.verified_true(user['email'])
        return {'succes': True}
    else:
        raise HTTPException(status_code=fastapi_status.HTTP_404_NOT_FOUND)


@app.get('/verified', include_in_schema=False)
async def handle_verified(request: Request):
    return templates.TemplateResponse('verified.html', {'request': request})


@app.get('/login', response_class=HTMLResponse, tags=['account'])
async def login(request: Request):
    """
    ## Страница входа пользователя в ЛК
    Содержит форму с емейлом, паролем
    """
    return templates.TemplateResponse(request=request, name='login.html', context={'message': None})


@app.post('/login', response_class=HTMLResponse, tags=['account'])
async def handle_login(request: Request, form: Login = Form()):
    """
    ## Обработка присланной формы на странице входа в ЛК
    Проверка наличия пользователя в бд
    Проверка введенного пароля с хэшем в бд
    В случае удачной проверки добавляются куки и делается редирект в ЛК
    """
    # ищем пользователя в бд по почте
    user = await pg.users.get(form.email)
    # если такая почта есть, то делаем проверку хэша пароля
    if user is not None:
        verify_psw_hash = verify_password(form.password, user['psw_hash'])
    else:
        verify_psw_hash = False
    # если хэш не прошел проверку отображаем уведомление
    # в остальных случаем выставляем куки для сессии
    if verify_psw_hash is False:
        return templates.TemplateResponse(request=request, name='login.html', context={'message': 'Введены неверные данные'})
    else:
        access_cookie = create_access_token(
            form.email, 'cookie', expires_delta=timedelta(days=ACCESS_COOKIE_EXPIRE_DAYS)
        )
        # Установка куки
        response = RedirectResponse(url='/me', status_code=303)
        response.set_cookie(key='user_session', value=access_cookie, httponly=True, max_age=ACCESS_COOKIE_EXPIRE_DAYS * 24 * 60 * 60, samesite='strict')
        return response


@app.get('/me', response_class=HTMLResponse, tags=['account'])
async def me(request: Request, user_session: Optional[str] = Cookie(None)):
    """
    ## ЛК пользователя
    Проверяются куки и отображается информация  с именем и токеном
    """
    # проверяем есть ли куки у пользователя
    if user_session:
        # находим пользователя по кукам, если находится отображаем ЛК
        # в остальных случаем удаляем неверные куки
        user = await check_token(user_session, 'cookie', None, None)
        if type(user) is dict:
            return templates.TemplateResponse('me.html', {'request': request, 'name': user['name'], 'token': user['token']})
        else:
            response = RedirectResponse(url='/', status_code=303)
            response.delete_cookie('user_session')
            return response
    else:
        return templates.TemplateResponse('me.html', {'request': request, 'name': None, 'token': None})


@app.post('/logout', response_class=HTMLResponse, tags=['account'])
async def logout():
    """
    ## Ссылка для выхода пользователя из ЛК
    Удаляются куки и делается редирект на главную страницу
    """
    response = RedirectResponse(url='/', status_code=303)
    response.delete_cookie('user_session')
    return response


@app.put('/task', tags=['task'], status_code=fastapi_status.HTTP_201_CREATED,
         dependencies=[Depends(RateLimiter(times=5, minutes=1))],
         summary='Добавление задачи',
         response_description='Успешное добавление - возврат статуса и идентификатора')
async def task_add(user: dict = Depends(get_user_from_token),
                   item: TaskAdd = Body()) -> Answer:
    """
    ## Добавление задачи
    Позволяет добавить задачу с полями:
       * title - Заголовок
       * description - Описание
       * level - Приоритет
       * dt_to - Дата дедлайна
    """
    # добавление информации по задаче в бд
    data = await pg.tasks.add(user['email'], item)
    if not data:
        raise HTTPException(status_code=fastapi_status.HTTP_400_BAD_REQUEST)
    return Answer(status=True, id=data['id'])


@app.post("/uploadfile/", deprecated=True)
async def create_upload_file(file: UploadFile):
    pass


@app.get('/task', tags=['task'], deprecated=True)
async def task_get_all(user: dict = Depends(get_user_from_token)):
    pass


@app.post('/task', tags=['task'], deprecated=True)
async def task_delete(user: dict = Depends(get_user_from_token)):
    pass


@app.patch('/task/setstatus', tags=['task'], deprecated=True)
async def task_delete(user: dict = Depends(get_user_from_token)):
    pass


@app.patch('/task/update', tags=['task'], deprecated=True)
async def task_update(user: dict = Depends(get_user_from_token)):
    pass


if __name__ == "__main__":
    uvicorn.run("main:app", reload=True, use_colors=True, workers=4)
