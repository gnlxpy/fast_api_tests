from config import settings
from datetime import timedelta
from fastapi import Form, Cookie, HTTPException, Request, Path, status as fastapi_status, APIRouter
from typing import Optional
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from encryption import hash_password, create_access_token, check_token, verify_password, TokenTypes
from models import Registration, Login
from sql_handler_v2 import Pg
from tasks import send_email_task


router = APIRouter(
    prefix="/lk",
    tags=["lk"]
)


# Подключение к папке с шаблонами
templates = Jinja2Templates(directory='templates')


@router.get('/', response_class=HTMLResponse)
async def index(request: Request):
    """
    ## Главная страница
    Содержит кнопку регистрация и логин
    """
    return templates.TemplateResponse(request=request, name='index.html')


@router.get('/registration', response_class=HTMLResponse)
async def registration(request: Request):
    """
    ## Страница регистрации пользователя
    Содержит форму с Именем, емейлом, паролем
    """
    return templates.TemplateResponse(request=request, name='registration.html', context={'message': None})


@router.post('/registration')
async def handle_registration(request: Request, form: Registration = Form()):
    """
    ## Обработка присланной формы на странице регистрации
    Проверка повтора пароля и наличия емейл в бд
    Создается токен пользователя для апи
    Пользователь добавляется в бд
    Редирект на страницу логина
    """
    email = str(form.email)
    # проверяем существующих пользователей
    user = await Pg.Users.get(email)
    if user:
        return templates.TemplateResponse(request=request, name='registration.html', context={'message': 'Пользователь уже существует'})
    # создаем хэш пароля и токен пользователя
    password_hashed = hash_password(form.password)
    access_token = create_access_token(email, TokenTypes.BEARER)
    confirm_token = create_access_token(email, TokenTypes.CONFIRM)
    # отправка почты
    send_email_task.delay(email, form.username, f'{settings.SERVER_URL}/lk/confirm/{confirm_token}')
    # добавляем пользователя в бд
    await Pg.Users.add(form, password_hashed, access_token)
    # переадресовываем для первого входа в ЛК
    return templates.TemplateResponse(request=request, name='login.html', context={'message': 'Регистрация прошла успешно, войдите для продолжения.'})


@router.get('/confirm/{confirm_code}', include_in_schema=False)
async def confirmation_email(request: Request, confirm_code: str = Path()):
    user = await check_token(confirm_code, 'confirm', request.client.host, '/confirm')
    if user:
        await Pg.Users.verified_true(user['email'])
        return RedirectResponse(url='/lk/verified', status_code=303)
    else:
        raise HTTPException(status_code=fastapi_status.HTTP_404_NOT_FOUND)


@router.get('/verified', include_in_schema=False)
async def handle_verified(request: Request):
    return templates.TemplateResponse(request=request, name='verified.html')


@router.get('/login', response_class=HTMLResponse, tags=['account'])
async def login(request: Request):
    """
    ## Страница входа пользователя в ЛК
    Содержит форму с емейлом, паролем
    """
    return templates.TemplateResponse(request=request, name='login.html', context={'message': None})


@router.post('/login', response_class=HTMLResponse)
async def handle_login(request: Request, form: Login = Form()):
    """
    ## Обработка присланной формы на странице входа в ЛК
    Проверка наличия пользователя в бд
    Проверка введенного пароля с хэшем в бд
    В случае удачной проверки добавляются куки и делается редирект в ЛК
    """
    email = str(form.email)
    # ищем пользователя в бд по почте
    user = await Pg.Users.get(email)
    # если такая почта есть, то делаем проверку хэша пароля
    if user:
        verify_psw_hash = verify_password(form.password, user['psw_hash'])
        if verify_psw_hash:
            access_cookie = create_access_token(email, TokenTypes.COOKIE)
            # Установка куки
            response = RedirectResponse(url='/lk/me', status_code=303)
            response.set_cookie(key='user_session', value=access_cookie, httponly=True,
                                max_age=settings.ACCESS_COOKIE_EXPIRE_DAYS * 24 * 60 * 60, samesite='strict')
            return response
    return templates.TemplateResponse(request=request, name='login.html', context={'message': 'Введены неверные данные'})


@router.get('/me', response_class=HTMLResponse)
async def me(request: Request, user_session: Optional[str] = Cookie(None)):
    """
    ## ЛК пользователя
    Проверяются куки и отображается информация  с именем и токеном
    """
    # проверяем есть ли куки у пользователя
    if user_session:
        # находим пользователя по кукам, если находится отображаем ЛК
        # в остальных случаем удаляем неверные куки
        user = await check_token(user_session, TokenTypes.COOKIE, None, None)
        if user:
            return templates.TemplateResponse(request=request, name='me.html', context={'name': user['name'], 'token': user['token']})
    return templates.TemplateResponse(request=request, name='me.html', context={'name': None, 'token': None})


@router.post('/logout', response_class=HTMLResponse)
async def logout():
    """
    ## Ссылка для выхода пользователя из ЛК
    Удаляются куки и делается редирект на главную страницу
    """
    response = RedirectResponse(url='/lk', status_code=303)
    response.delete_cookie('user_session')
    return response
