import asyncio
import datetime
import traceback
import asyncpg
from models import TaskAdd, Registration
from config import settings


SETTINGS = settings

def init_close_pg(def_decorate):
    """
    Инициализация соединения БД Постгрес
    """
    async def wrapper(*args, **kwargs):
        try:
            conn = await asyncpg.connect(settings.POSTGRES_URL)
        except Exception:
            traceback.print_exc()
            return False
        try:
            if conn:
                result = await def_decorate(*args, **kwargs, conn=conn)
                return result
        except Exception:
            traceback.print_exc()
            return False
        finally:
            if conn:
                await conn.close()  # Закрытие соединения с БД после выполнения
    return wrapper


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
        @init_close_pg
        async def add(form: Registration, password_hashed: bytes, access_token: str, conn: asyncpg.Connection) -> bool:
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


        @staticmethod
        @init_close_pg
        async def get_all(conn) -> list[dict]:
            return await conn.fetch('SELECT * FROM Users;')

        @staticmethod
        @init_close_pg
        async def get(email: str, conn) -> dict | bool:
            result = await conn.fetch(
                f'''
                SELECT *
                FROM Users
                WHERE email = $1;
                ''', email)
            return result[0] if result is not False else False

        @staticmethod
        @init_close_pg
        async def verified_true(email: str, conn) -> bool:
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

    # Операции над задачами
    class Tasks:

        @staticmethod
        @init_close_pg
        async def add(email: str, task: TaskAdd, conn) -> dict | bool:
            result = await conn.fetch(
                '''
                INSERT INTO Tasks (email, title, description, status, level, dt_to, dt)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING id;
                ''',
                email, task.title, task.description, 'WAIT', task.level, task.dt_to,
                datetime.datetime.now().replace(microsecond=0)
            )
            return result[0] if result is not False else False

        @staticmethod
        @init_close_pg
        async def get_all(email: str, conn) -> list | bool:
            result = await conn.fetch('SELECT * FROM Tasks WHERE email = $1;', email)
            return result

        @staticmethod
        @init_close_pg
        async def get(id: int, conn) -> dict | bool:
            result = await conn.fetch('SELECT * FROM Tasks WHERE id = $1;', id)
            return result[0] if result is not False else False

        @staticmethod
        @init_close_pg
        async def delete(id: int, conn) -> bool:
            result = await conn.fetch(
                '''
                DELETE FROM Tasks
                WHERE id = $1
                RETURNING id;
                ''',
                id
            )
            return True if len(result) > 0 else False

        @staticmethod
        @init_close_pg
        async def upd(email: str, id: int, data: dict, conn) -> bool:
            set_str = prepare_data_to_upd(data)
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

    class Dev:

        @staticmethod
        @init_close_pg
        async def truncate(table: str, conn) -> bool:
            await conn.execute(f'TRUNCATE TABLE "{table}" RESTART IDENTITY CASCADE;')
            result = await conn.fetchval(f'SELECT COUNT(*) FROM "{table}";')
            return True if result == 0 else False


# async def conn_new():
#     r = await Pg.Users.get_all()
#     print(r)


if __name__ == '__main__':
    pass
