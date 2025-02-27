from io import BytesIO
import aioboto3
from contextlib import asynccontextmanager
import traceback
from config import settings


@asynccontextmanager
async def init_connection():
    session = aioboto3.Session()
    async with session.client('s3',
                        endpoint_url=f'http://{settings.HOST}:9000',  # URL MinIO
                        aws_access_key_id=settings.S3_ACCESS,  # Твой ключ доступа
                        aws_secret_access_key=settings.S3_SECRET,  # Твой секретный ключ
                        region_name='us-east-1') as s3:
        yield s3


async def upload_file(file: BytesIO, filename):
    try:
        async with init_connection() as s3:
            response = await s3.upload_fileobj(file, settings.BUCKET_NAME, filename)
            print(response)
            return True
    except Exception:
        traceback.print_exc()
        return False


async def delete_file(object_key: str) -> bool:
    try:
        async with init_connection() as s3:
            # проверка наличия объекта
            try:
                response = await s3.get_object(Bucket=settings.BUCKET_NAME, Key=object_key)
            except s3.exceptions.NoSuchKey:
                return False
            # удаление
            await s3.delete_object(Bucket=settings.BUCKET_NAME, Key=object_key)
            # проверка наличия после удаления
            try:
                response = await s3.get_object(Bucket=settings.BUCKET_NAME, Key=object_key)
                print(response)
            except s3.exceptions.NoSuchKey:
                return True
    except Exception:
        traceback.print_exc()
        return False
