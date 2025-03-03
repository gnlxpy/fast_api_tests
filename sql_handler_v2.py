import asyncio
import datetime
import traceback

import asyncpg
from models import TaskAdd, Registration
from config import settings


SETTINGS = settings


async def init_pg():
    """
    Инициализация БД Постгрес
    :return: глобальная переменная с соединением
    """
    global pool
    pool = await asyncpg.create_pool(settings.POSTGRES_URL, min_size=1, max_size=5)
    return pool


async def close_pg():
    """
    Закрытие соединения
    """
    await pool.close()


def prepare_data_to_upd(data: dict) -> str:
    """
    Преобразование словаря в текст для выгрузки в БД
    """
    parts = []
    for k, v in data.items():
        value = f"'{v}'" if isinstance(v, str) else str(v)
        parts.append(f"{k} = {value}")
    return ", ".join(parts)


class Pg:

    # Операции над пользователями
    class Users:

        @staticmethod
        async def add(form: Registration, password_hashed: bytes, access_token: str) -> bool:
            try:
                async with pool.acquire() as conn:
                    result = await conn.fetch(
                        '''
                        INSERT INTO Users (email, psw_hash, name, token, status, dt)
                        VALUES ($1, $2, $3, $4, $5, $6)
                        RETURNING email;
                        ''',
                        form.email,
                        password_hashed,
                        form.username,
                        access_token,
                        'NEW',
                        datetime.datetime.now().replace(microsecond=0)
                    )
                    return True if result else False
            except Exception:
                return False

        @staticmethod
        async def get_all() -> list[dict]:
            async with pool.acquire() as conn:
                return await conn.fetch('SELECT * FROM Users;')

        @staticmethod
        async def get(email: str) -> dict | bool:
            try:
                async with pool.acquire() as conn:
                    result = await conn.fetch(
                        f'''
                        SELECT *
                        FROM Users
                        WHERE email = $1;
                        ''', email)
                    return result[0]
            except Exception:
                return False

        @staticmethod
        async def verified_true(email: str) -> bool:
            try:
                async with pool.acquire() as conn:
                    result = await conn.fetch(
                        '''
                        UPDATE Users
                        SET verified = TRUE
                        WHERE email = $1
                        RETURNING email;
                        ''',
                        email
                    )
                    return True if result else False
            except Exception:
                return False

    # Операции над задачами
    class Tasks:

        @staticmethod
        async def add(email: str, task: TaskAdd) -> dict | bool:
            try:
                async with pool.acquire() as conn:
                    result = await conn.fetch(
                        '''
                        INSERT INTO Tasks (email, title, description, status, level, dt_to, dt)
                        VALUES ($1, $2, $3, $4, $5, $6, $7)
                        RETURNING id;
                        ''',
                        email, task.title, task.description, 'WAIT', task.level, task.dt_to,
                        datetime.datetime.now().replace(microsecond=0)
                    )
                    return result[0]
            except Exception:
                return False

        @staticmethod
        async def get_all(email: str) -> list | bool:
            try:
                async with pool.acquire() as conn:
                    result = await conn.fetch('SELECT * FROM Tasks WHERE email = $1;', email)
                    return result
            except Exception:
                return False

        @staticmethod
        async def get(id: int) -> dict | bool:
            try:
                async with pool.acquire() as conn:
                    result = await conn.fetch('SELECT * FROM Tasks WHERE id = $1;', id)
                    return result[0]
            except Exception:
                return False

        @staticmethod
        async def delete(id: int) -> bool:
            try:
                async with pool.acquire() as conn:
                    result = await conn.fetch(
                        '''
                        DELETE FROM Tasks
                        WHERE id = $1
                        RETURNING id;
                        ''',
                        id
                    )
                    return True if len(result) > 0 else False
            except Exception:
                return False

        @staticmethod
        async def upd(email: str, id: int, data: dict) -> bool:
            try:
                async with pool.acquire() as conn:
                    set_str = prepare_data_to_upd(data)
                    print('set_str', set_str)
                    result = await conn.fetch(
                        f'''
                        UPDATE Tasks
                        SET {set_str}
                        WHERE email = $1 and id = $2
                        RETURNING id;
                        ''',
                        email, id
                    )
                    return True if result else False
            except Exception:
                traceback.print_exc()
                return False

    class Dev:

        @staticmethod
        async def truncate(table: str) -> bool:
            async with pool.acquire() as conn:
                await conn.execute(f'TRUNCATE TABLE "{table}" RESTART IDENTITY CASCADE;')
                result = await conn.fetchval(f'SELECT COUNT(*) FROM "{table}";')
                return True if result == 0 else False


if __name__ == '__main__':
    pass
