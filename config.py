from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import IPvAnyAddress, EmailStr, HttpUrl


class Settings(BaseSettings):
    HOST: str
    SECRET_KEY: str
    POSTGRES_USER: str
    POSTGRES_PSW: str
    POSTGRES_DB: str
    REDIS_PSW: str
    EMAIL_USER: str
    EMAIL_PSW: str
    S3_ACCESS: str
    S3_SECRET: str
    BUCKET_NAME: str
    SERVER_URL: HttpUrl
    ACCESS_TOKEN_EXPIRE_DAYS: int
    ACCESS_COOKIE_EXPIRE_DAYS: int
    UPLOAD_SIZE: int

    @property
    def REDIS_URL(self):
        return f"redis://default:{self.REDIS_PSW}@{self.HOST}:6379/0"

    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')


settings = Settings()
