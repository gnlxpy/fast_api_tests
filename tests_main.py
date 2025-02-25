import datetime
import os
import json
import traceback
from enum import Enum
from main import app
from fastapi.testclient import TestClient
import pytest
from models import TaskAdd, Answer


client = TestClient(app)

HEADERS = {'Authorization': f'Bearer {os.getenv("TEST_USER_TOKEN")}'}


class TypesRequests(Enum):
    """
    Возможные типы запросов
    """
    GET = client.get
    POST = client.post
    PUT = client.put
    PATCH = client.patch


@pytest.mark.parametrize(
    'url, expected_status_code, expected_text',
    [
        ('/lk', 200, 'Добро пожаловать на сайт To-Do mini'),
        ('/lk/login', 200, 'Вход'),
        ('/lk/registration', 200, 'Регистрация'),
        ('/lk/me', 200, 'Привет, незнакомец'),
        ('/lk/verified', 200, 'Вы успешно подтвердили свою почту'),
    ]
)
def test_get_lk(url: str, expected_status_code: int, expected_text: str):
    response = client.get(url)
    assert response.status_code == expected_status_code
    assert "text/html" in response.headers["content-type"]
    assert expected_text in response.text


@pytest.mark.parametrize(
    'url, _type, data, expected_status_code, expected_answer',
    [
        ('/task', TypesRequests.PUT, {'title': 'Test1', 'description': 'Test Description', 'level': 1, 'dt_to': '2025-03-01 12:00'}, 201, True)
    ]
)
def test_tasks(url: str, _type: TypesRequests, data: dict, expected_status_code: int, expected_answer: dict):
    try:
        pydantic = TaskAdd(**data)
    except Exception:
        traceback.print_exc()

    response = client.put(url=url, headers=HEADERS, json=data)

    try:
        response_obj = response.json()
        try:
            pydantic = Answer(**response_obj)
        except Exception:
            traceback.print_exc()
    except Exception:
        traceback.print_exc()
        response_obj = {'status': False}

    assert response.status_code == expected_status_code
    assert "application/json" in response.headers["content-type"]
    assert response_obj['status'] == expected_answer
