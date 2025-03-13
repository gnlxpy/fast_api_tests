import pytest
import pytest_asyncio
from pytest_asyncio import is_async_test
from config import settings
from encryption import hash_password, create_access_token, TokenTypes
from models import Registration
from sql_handler_v2 import Pg
from tests.unit.test_sql_handler import User


def pytest_collection_modifyitems(items):
    pytest_asyncio_tests = (item for item in items if is_async_test(item))
    session_scope_marker = pytest.mark.asyncio(loop_scope="session")
    for async_test in pytest_asyncio_tests:
        async_test.add_marker(session_scope_marker, append=False)


@pytest_asyncio.fixture(scope='module', autouse=True)
async def setup_db():
    global pool
    assert settings.POSTGRES_DB == 'test_postgres'
    yield
    r = await Pg.Dev.truncate('users')
    assert r == True
    r = await Pg.Dev.truncate('tasks')
    assert r == True


@pytest_asyncio.fixture(scope='session')
def user():
    form = Registration(
        username='Test',
        password='Test123*',
        confirm_password='Test123*',
        email='test@test.com'
    )
    password_hashed = hash_password(form.password)
    access_token = create_access_token(str(form.email), TokenTypes.BEARER)
    cookie = create_access_token(str(form.email), TokenTypes.COOKIE)
    return User(
        form=form,
        password_hashed=password_hashed,
        access_token=access_token,
        cookie={'user_session': cookie}
    )
