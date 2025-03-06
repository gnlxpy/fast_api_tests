import pytest
from main import app
from fastapi.testclient import TestClient
from bs4 import BeautifulSoup

client = TestClient(app)

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
