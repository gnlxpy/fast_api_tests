from contextlib import asynccontextmanager
import redis.asyncio as redis
import os

from dotenv import load_dotenv

load_dotenv()
REDIS_PSW = os.getenv('REDIS_PSW')
HOST = os.getenv('HOST')


@asynccontextmanager
async def redis_conn():
    connection = redis.from_url(f"redis://default:{REDIS_PSW}@{HOST}:6379/0", encoding="utf8", decode_responses=True)
    try:
        yield connection
    finally:
        await connection.close()


async def redis_add_key(key: str, value: str, ex: int) -> None:
    """
    Добавление ключа в бд Редис
    :param key: ключ
    :param value: значени
    :param ex: срок действия
    :return:
    """
    async with redis_conn() as r:
        await r.set(key, value, ex=ex)
