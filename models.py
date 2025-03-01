from enum import Enum
from typing import Annotated, Optional
from pydantic import BaseModel, Field, EmailStr, model_validator, HttpUrl
import datetime
import re


class FormValidationError(ValueError):
    """Кастомное исключение для ошибок модели Registration."""
    pass


class Registration(BaseModel):
    """
    Модель для регистрации ЛК
    ::def check_passwords_match:: Валидатор имени и паролей
    """
    username: Annotated[str, Field(...)]
    password: Annotated[str, Field(...)]
    confirm_password: Annotated[str, Field(...)]
    email: Annotated[EmailStr, Field(...)]

    @model_validator(mode='before')
    def check_passwords_match(cls, values):
        username = values.get('username')
        password = values.get('password')
        confirm_password = values.get('confirm_password')

        if 20 < len(username) < 4 or re.search(r'[\W_]', username):
            raise FormValidationError('Имя должно быть от 4 до 20 символов и не должно содержать спецсимволов')
        if 6 > len(password) or len(confirm_password) > 32:
            raise FormValidationError('Пароль должен быть от 6 до 32 символов')
        if password != confirm_password:
            raise FormValidationError('Пароли не совпадают')
        if not re.search(r'[A-Z]', password):
            raise FormValidationError('Пароль должен содержать хотя бы одну заглавную букву.')
        if not re.search(r'[a-z]', password):
            raise FormValidationError('Пароль должен содержать хотя бы одну строчную букву.')
        if not re.search(r'[\W_]', password):  # спецсимвол
            raise FormValidationError('Пароль должен содержать хотя бы один спецсимвол.')

        return values


class Login(BaseModel):
    """
    Модель логина пользователя ЛК
    """
    email: Annotated[EmailStr, Field(...)]
    password: Annotated[str, Field(...)]


class TaskAdd(BaseModel):
    """
    Модель добавления задачи
    -title
    -description
    -level
    -dt_to
    """
    title: Annotated[str, Field(..., min_length=3, max_length=128, description='Название задачи')]
    description: Annotated[Optional[str], Field(default=None, min_length=3, max_length=255, description='Описание задачи')]
    level: Annotated[int, Field(default=0, ge=0, le=3, description='Уровень важности задачи')]
    dt_to: Annotated[Optional[datetime.datetime], Field(default=None, description='Дедлайн задачи')]

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    'title': 'Сделать покупки',
                    'description': 'Молоко, сыр, вино',
                    'level': 1,
                    'dt_to': '2011-11-04T00:05:23'
                }
            ]
        }
    }


class Answer(BaseModel):
    """
    Модель ответа АПИ
    """
    status: Annotated[bool, Field(..., description='Статус')]
    id: Annotated[Optional[int] | None, Field(default=None, description='id созданной задачи')]

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    'status': True,
                    'id': 113
                }
            ]
        }
    }

class TasksList(BaseModel):
    status: Annotated[bool, Field(..., description='Статус')]
    data: Annotated[Optional[list[dict]] | None, Field(default=None, description='Список задач')]

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    'status': True,
                    'data': [
                        {}
                    ]
                }
            ]
        }
    }


class AnswerUrl(Answer):
    """
    Модель ответа АПИ (c url)
    """
    url: Annotated[HttpUrl, Field(description='Url загруженного файла для скачивания')]

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    'status': True,
                    'id': 113,
                    'url': 'http://{{ Your Domain }}/api/v1/buckets/tasksfiles/objects/download?prefix={{ File Name }}. {{ File Ext }}'
                }
            ]
        }
    }


class Statuses(Enum):
    IN_PROGRESS = 'IN_PROGRESS'
    WAIT = 'WAIT'
    DONE = 'DONE'
    ARCHIVE = 'ARCHIVE'


class SetStatus(BaseModel):
    id: Annotated[Optional[int] | None, Field(..., description='id созданной задачи')]
    status: Annotated[Statuses, Field(..., description='Один из возможных статусов')]

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    'id': 113,
                    'status': 'DONE'
                }
            ]
        }
    }
