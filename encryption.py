import random
import string
import jwt
import bcrypt
import datetime
from dotenv import load_dotenv
from redis_handler import redis_add_key
from sql import PgActions
from config import settings


# константы для хеширования паролей
ALGORITHM = 'HS256'
# временный словарь для отслеживания ip пользователей
CLIENT_HOSTS = {}
# объект для работы с постгрес
pg = PgActions()


def generate_code(length):
    result = ''
    while length != 0:
        length -= 1
        result += f'{random.randint(0, 9)}'
    return result


def generate_filename(length: int) -> str:
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def hash_password(password: str) -> bytes:
    """
    Создание хэша пароля
    """
    password = password.encode("utf-8")
    salt = bcrypt.gensalt()  # Генерация случайной соли
    hashed_password = bcrypt.hashpw(password, salt)
    return hashed_password


def verify_password(plain_password: str, hashed_password: bytes) -> bool:
    """
    Проверка пароля
    """
    plain_password_bytes = plain_password.encode("utf-8")
    return bcrypt.checkpw(plain_password_bytes, hashed_password)


def create_access_token(email: str, type_token: str, expires_delta: datetime.timedelta | None = None):
    """
    Создание токена
    :param email: почта пользователя
    :param type_token: тип токена bearer | cookie
    :param expires_delta: время действия токена (дни)
    :return: зашифрованный JWT-токен
    """
    # время жизни токена
    expire = datetime.datetime.now() + expires_delta
    # данные внутри токена
    payload = {
        'email': email,
        'type_token': type_token,
        'exp': expire
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


async def check_clients_dict(client_host: str, path: str) -> None:
    """
    Увеличение счетчика ошибок по айпи пользователей
    :param client_host: айпи клиента
    :param path: ссылка
    :return: None
    """
    if client_host not in CLIENT_HOSTS.keys():
        CLIENT_HOSTS[client_host] = 1
    else:
        CLIENT_HOSTS[client_host] += 1
        if CLIENT_HOSTS[client_host] >= 10:
            await redis_add_key(f'fastapi-limiter:{client_host}:{path}:12:0', '10', 3600)
            CLIENT_HOSTS[client_host] = 0


async def check_token(token: str, type_token: str, client_host: str | None, path: str | None) -> dict | bool:
    """
    Проверка токена пользователя
    :param token: токен
    :param type_token: тип токена bearer | cookie
    :param client_host: айпи пользоваетеля
    :param path: ссылка
    :return: True | False
    """
    # получаем данные пользователя из токена
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    except Exception:
        # добавляем в список пользователей с ошибкой
        await check_clients_dict(client_host, path) if client_host is not None else None
        return False
    try:
        # определяем тип, почту, срок действия токена
        type_, email, exp = payload.get('type_token'), payload.get('email'), payload.get('exp')
        # сверяем тип и срок действия
        if type_token != type_ or exp < datetime.datetime.now().timestamp():
            await check_clients_dict(client_host, path) if client_host is not None else None
            return False
        # определяем и возвращаем пользователя
        user = await pg.users.get(email)
        return user
    except Exception:
        await check_clients_dict(client_host, path) if client_host is not None else None
        return False


if __name__ == '__main__':
    pass