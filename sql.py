import os
import datetime
from dotenv import load_dotenv
import asyncpg
import traceback
from logs import logger
from models import TaskAdd, Registration
# import asyncio

# локальная загрузка переменных
load_dotenv()

HOST = os.getenv('HOST')
POSTGRES_USER = os.getenv('POSTGRES_USER')
POSTGRES_PSW = os.getenv('POSTGRES_PSW')


async def sql_execute(sql_script: str, data: any = None) -> list | bool:
    """
    Функция для выполнения скриптов в бд
    :param sql_script: скрипт
    :param data: данные для выгрузки
    :return: список с ответом | False
    """
    # инициализация бд
    try:
        conn = await asyncpg.connect(user=POSTGRES_USER, password=POSTGRES_PSW,
                                 database='postgres', host=HOST)
    except Exception:
        logger.critical(f'Error sql connection \n{traceback.format_exc()}')
        return False
    # выполнение скрипта с данными в запросе и без
    try:
        if data != None and type(data) is tuple:
            select = await conn.fetch(sql_script, *data)
        else:
            select = await conn.fetch(sql_script)
        select_dicts = [dict(x) for x in select]
        return select_dicts
    except Exception:
        logger.critical(f'Error sql script \n{traceback.format_exc()}')
        return False
    # закрытие соединения
    finally:
        if conn:
            await conn.close()


class PgActions:
    def __init__(self):
        self.users = self.Users(self)
        self.tasks = self.Tasks(self)

    class Users:
        def __init__(self, outer_instance):
            self.outer = outer_instance

        async def add(self, form: Registration, password_hashed, access_token) -> bool:
            """
            Добавление пользователя
            :param form: объект с данными из формы регистрации
            :param password_hashed: хэшированный пароль
            :param access_token: токен пользователя для ЛК
            :return: True | False
            """
            result = await sql_execute(f'''
            INSERT INTO Users (email, psw_hash, name, token, status, dt)
            VALUES ($1, $2, $3, $4, $5, $6);
            ''', (
                form.email,
                password_hashed,
                form.username,
                access_token,
                'NEW',
                datetime.datetime.now().replace(microsecond=0)
            ))
            if len(result) != 0:
                return True
            else:
                return False

        async def get_all(self) -> list[dict]:
            result = await sql_execute('''
            SELECT *
            FROM Users
            ''')
            return result

        async def get(self, email: str) -> dict | bool:
            result = await sql_execute(f'''
            SELECT *
            FROM Users
            WHERE email = '{email}'
            ''')
            if len(result) == 0:
                return False
            else:
                return result[0]

    class Tasks:
        def __init__(self, outer_instance):
            self.outer = outer_instance

        async def add(self, email: str, task: TaskAdd):
            result = await sql_execute(f'''
            INSERT INTO Tasks (email, title, description, status, level, dt_to, dt)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING id;
            ''', (
                email,
                task.title,
                task.description,
                'WAIT',
                task.level,
                task.dt_to,
                datetime.datetime.now().replace(microsecond=0)
            ))
            return result[0]

        async def get_all(self, email: str):
            result = await sql_execute(f'''
            SELECT *
            FROM Tasks
            WHERE email = '{email}'
            ''')
            if len(result) == 0:
                return None
            else:
                return result

        async def delete(self, id: int):
            result = await sql_execute(f'''
            DELETE FROM Tasks
            WHERE id = $1
            RETURNING id
            ''', id)
            return result

        async def upd(self, email: str, id: int, data: dict):
            set_str = ''
            for k, v in data.items():
                if type(v) is str:
                    set_str += f"{k} = '{v}',"
                else:
                    set_str += f"{k} = {v},"
            set_str = set_str[:-1]
            # Составляем SQL-запрос
            sql_script = f'''
            UPDATE Tasks
            SET {set_str}
            WHERE email = $1 and id = $2
            RETURNING id;
            '''
            result = await sql_execute(sql_script, (email, id))
            return result


async def create_table():
    sql = '''
CREATE TABLE IF NOT EXISTS Tasks (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description VARCHAR(255),
    status VARCHAR(255) NOT NULL,
    level INT,
    dt_to TIMESTAMP,
    dt TIMESTAMP NOT NULL,
    CONSTRAINT fk_email FOREIGN KEY (email) REFERENCES Users (email)
);
    '''
    conn = await asyncpg.connect(user=POSTGRES_USER, password=POSTGRES_PSW,
                                 database='postgres', host=HOST)
    await conn.execute(sql)
    await conn.close()
    return True


# async def exec():
#     pg = PgActions()
#     task_list = {
#         'description': 'One',
#     }
#     s = await pg.tasks.upd('den@ya.ru', 11, {'dt_to': '2025-02-01 12:00'})
#     print(s)
#     return True
