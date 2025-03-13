import time
import asyncio
import pytest
import pytest_asyncio
from main import app
from fastapi.testclient import TestClient
from bs4 import BeautifulSoup
from sql_handler_v2 import Pg


client = TestClient(app)


@pytest.fixture(scope='function')
def add_user_cookies(user):
    client = TestClient(app)
    client.cookies.set('user_session', user.cookie['user_session'])
    return client


@pytest_asyncio.fixture(scope='module', autouse=True)
async def user_db(user):
    r = await Pg.Users.add(
        user.form,
        user.password_hashed,
        user.access_token
    )
    assert r == True
    await asyncio.sleep(1)


@pytest.mark.parametrize(
    'url, elements',
    [
        ('/lk', (
            {'text': 'Добро пожаловать на сайт To-Do mini'},
            {'a': ('href', '/lk/registration')},
            {'a': ('href', '/lk/login')}
         )),
        ('/lk/login', (
            {'text': 'Вход'},
            {'input': ('id', 'email')},
            {'input': ('id', 'password')}
        )),
        ('/lk/registration', (
                {'text': 'Регистрация'},
                {'input': ('id', 'username')},
                {'input': ('id', 'password')},
                {'input': ('id', 'confirm_password')},
                {'input': ('id', 'email')}
        )),
        ('/lk/verified', (
                {'text': 'Вы успешно подтвердили свою почту'},
                {'a': ('href', '/lk/me')},
        )),
        ('/lk/me', (
                {'text': 'Добро пожаловать'},
                {'form': ('action', '/lk/login')},
        ))
    ]
)
def test_web(url, elements):
    r = client.get(url)

    assert r.status_code == 200
    assert r.headers["content-type"] == 'text/html; charset=utf-8'
    assert 'https://cdn.jsdelivr.net/npm/bootstrap@5.0.2/dist/css/bootstrap.min.css' in r.text
    assert 'link rel="icon"' in r.text

    soup = BeautifulSoup(r.text, "html.parser")
    for element in elements:
        for k, v in element.items():
            if k == 'text':
                assert v in r.text
            else:
                item = soup.find(k, {v[0]: v[1]})
                assert item is not None


@pytest.mark.parametrize(
    'url, status_code', [
        ('/lk/me', 200)
    ]
)
@pytest.mark.usefixtures('add_user_cookies')
def test_auth(url, status_code, user, add_user_cookies):
    client = add_user_cookies
    r = client.get(url, follow_redirects=True)
    assert r.status_code == status_code
    assert 'Ваш токен' in r.text
    assert user.form.username in r.text
    assert user.access_token in r.text
