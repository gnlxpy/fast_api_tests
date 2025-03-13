import datetime
import pytest_asyncio
from pydantic import BaseModel
from sql_handler_v2 import Pg
from models import Registration, TaskAdd


class User(BaseModel):
    form: Registration
    password_hashed: bytes
    access_token: str
    cookie: dict


@pytest_asyncio.fixture(scope='module')
def task():
    return TaskAdd(
        title='Test1',
        description='Test description',
        level=1,
        dt_to=datetime.datetime(2025, 3, 8, 12, 0)
    )


@pytest_asyncio.fixture(scope='module')
def task_update():
    return TaskAdd(
        title='Test1 updated',
        description='Test description updated',
        level=2,
        dt_to=datetime.datetime(2025, 6, 1, 18, 30)
    )


class TestUsers:

    async def test_add(self, user):
        r = await Pg.Users.add(
            user.form,
            user.password_hashed,
            user.access_token
        )
        assert r == True

    async def get(self, user):
        r = await Pg.Users.get(str(user.form.email))
        assert r['email'] == str(user.form.email)

    async def test_get_all(self, user):
        r = await Pg.Users.get_all()
        users_emails = [i['email'] for i in r]
        assert str(user.form.email) in users_emails

    async def test_verified_true(self, user):
        r = await Pg.Users.get(str(user.form.email))
        assert r['verified'] is None
        await Pg.Users.verified_true(str(user.form.email))
        r = await Pg.Users.get(str(user.form.email))
        assert r['verified'] == True


class TestTasks:

    async def test_add(self, user, task):
        r = await Pg.Tasks.get_all(str(user.form.email))
        assert r == []
        r = await Pg.Tasks.add(str(user.form.email), task)
        assert r != False

    async def test_get(self, user, task):
        r = await Pg.Tasks.get(1)
        assert r['email'] == str(user.form.email)
        assert r['title'] == str(task.title)

    async def test_get_all(self, user, task):
        r = await Pg.Tasks.get_all(str(user.form.email))
        assert len(r) > 0
        assert r[0]['email'] == str(user.form.email)
        assert r[0]['title'] == str(task.title)

    async  def test_upd(self, user, task_update):
        r = await Pg.Tasks.upd(str(user.form.email), 1, {'description': task_update.description})
        assert r == True
        r = await Pg.Tasks.get(1)
        assert r['description'] == str(task_update.description)

    async def test_delete(self):
        r = await Pg.Tasks.delete(1)
        assert r == True
        r = await Pg.Tasks.get(1)
        assert r == False
