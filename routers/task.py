import os
from fastapi import Form, Depends, HTTPException, Request, Body, status as fastapi_status, UploadFile, File, APIRouter
from fastapi.security import OAuth2PasswordBearer
from fastapi_limiter.depends import RateLimiter
from encryption import check_token, generate_filename
from models import Answer, TaskAdd, AnswerUrl, TasksList, SetStatus
from sql_handler import PgActions, HOST
from io import BytesIO
from s3_handler import upload_file, delete_file


UPLOAD_SIZE = int(os.getenv('UPLOAD_SIZE'))
UPLOAD_EXT_TYPES = ('txt', 'jpg', 'jpeg', 'png', 'gif', 'pdf', 'doc', 'docx', 'xls', 'xlsx')


# объект бд постгрес
pg = PgActions()
# Извлечение токена из запросов
oauth2_scheme = OAuth2PasswordBearer(tokenUrl='token')


router = APIRouter(
    prefix="/task",
    tags=["task"]
)


async def get_user_from_token(request: Request, token: str = Depends(oauth2_scheme)) -> dict | bool:
    """
    Получаем пользователя из токена и проверяем его.
    """
    user = await check_token(token, 'bearer', request.client.host, '/task')
    if not user:
        raise HTTPException(status_code=fastapi_status.HTTP_403_FORBIDDEN, detail="Неверный токен или несуществующий пользователь")
    return user


async def get_upload(file: UploadFile = File(description='Объект файла (BytesIO)')):
    # считывание и проверка размера файла
    file_ext = file.filename.split('.')[1]
    if file.size > UPLOAD_SIZE:
        raise HTTPException(status_code=fastapi_status.HTTP_406_NOT_ACCEPTABLE, detail='Размер файла должен быть меньше 5мб')
    elif file_ext not in UPLOAD_EXT_TYPES:
        raise HTTPException(status_code=fastapi_status.HTTP_406_NOT_ACCEPTABLE, detail='Разрешены только текстовые файлы и изображения')
    file_content = await file.read()
    file_object = BytesIO(file_content)
    # сгенерировать имя файлу
    new_filename = f'{generate_filename(12)}.{file_ext}'
    return {'file_object': file_object, 'new_filename': new_filename}


@router.put('/', status_code=fastapi_status.HTTP_201_CREATED,
         # dependencies=[Depends(RateLimiter(times=5, minutes=1))],
         summary='Добавление задачи',
         response_description='Успешное добавление - возврат статуса и идентификатора')
async def task_add(user: dict = Depends(get_user_from_token),
                   item: TaskAdd = Body()
                   ) -> Answer:
    """
    ## Добавление задачи
    Позволяет добавить задачу с полями:
       * title - Заголовок
       * description - Описание
       * level - Приоритет
       * dt_to - Дата дедлайна
    """
    # добавление информации по задаче в бд
    data = await pg.tasks.add(user['email'], item)
    if not data:
        raise HTTPException(status_code=fastapi_status.HTTP_400_BAD_REQUEST)
    return Answer(status=True, id=data['id'])


@router.post('/uploadfile', status_code=fastapi_status.HTTP_200_OK,
          dependencies=[Depends(RateLimiter(times=5, minutes=1))],
          summary='Загрузка файла',
          response_description='Успешное добавление - обновление задачи, возврат ссылки на файл')
async def get_file(user: dict = Depends(get_user_from_token), file_dict = Depends(get_upload),
                             id: int = Form(description='id задачи к которой необходимо прикрепить файл')) -> AnswerUrl:
    """
    ## Добавление файла к задаче
    Позволяет добавить 1 файл до 5мб и получить ссылку на него:
        * id - id задачи к которой необходимо прикрепить файл
        * file - Объект файла (BytesIO)
    """
    # проверить наличие задачи с необходимым айди
    tasks_list = await pg.tasks.get_all(user['email'])
    tasks_ids = [task['id'] for task in tasks_list if task['file'] in [None, '']]
    if id not in tasks_ids or len(tasks_ids) == 0:
        raise HTTPException(status_code=fastapi_status.HTTP_404_NOT_FOUND, detail='id задачи не найден')
    # выгрузка файла в s3
    full_new_filename = f't-{id}-{file_dict["new_filename"]}'
    status = await upload_file(file_dict['file_object'], full_new_filename)
    if status is False:
        raise HTTPException(status_code=fastapi_status.HTTP_500_INTERNAL_SERVER_ERROR, detail='Ошибка добавления файла на сервер')
    # сделать запись ссылки на файл в бд
    url = f'http://{HOST}:9001/api/v1/buckets/tasksfiles/objects/download?prefix={full_new_filename}'
    await pg.tasks.upd(user['email'], id, {'file': url})
    return AnswerUrl(status=True, id=id, url=url)


@router.delete('/uploadfile', status_code=fastapi_status.HTTP_200_OK,
            dependencies=[Depends(RateLimiter(times=5, minutes=1))],
            summary='Удаление файла',
            response_description='Файл успешно удален')
async def del_file(user: dict = Depends(get_user_from_token),
                   id: int = Form(description='id задачи у которой необходимо удалить файл')):
    """
    ## Удаление файла задачи
    Позволяет удалить 1 прикрепленный файл:
        * id - id задачи у которой необходимо удалить файл
    """
    # проверить наличие задачи с необходимым айди
    task_dict = await pg.tasks.get(id)
    if task_dict['email'] != user['email']:
        raise HTTPException(status_code=fastapi_status.HTTP_404_NOT_FOUND, detail='Такая задача не найдена')
    if task_dict['file'] is None:
        raise HTTPException(status_code=fastapi_status.HTTP_404_NOT_FOUND, detail='Файл у данной задачи не найден')
    # получение имени файла из ссылки в БД
    try:
        filename = task_dict['file'].split('=')[1]
    except Exception:
        raise HTTPException(status_code=fastapi_status.HTTP_500_INTERNAL_SERVER_ERROR)
    # операция удаления в s3
    status = await delete_file(filename)
    if status is False:
        raise HTTPException(status_code=fastapi_status.HTTP_500_INTERNAL_SERVER_ERROR, detail='Ошибка удаления файла')
    # удаление ссылки в БД
    await pg.tasks.upd(user['email'], id, {'file': ''})
    return Answer(status=True, id=id)


@router.get('/', status_code=fastapi_status.HTTP_200_OK,
            dependencies=[Depends(RateLimiter(times=5, minutes=1))],
            summary='Получение списка задач',
            response_description='Успешный запрос')
async def task_get_all(user: dict = Depends(get_user_from_token)) -> TasksList:
    """
    ## Получение списка всех задач
    """
    tasks_list = await pg.tasks.get_all(user['email'])
    return TasksList(status=True, data=tasks_list)


@router.post('/delete', status_code=fastapi_status.HTTP_200_OK,
            dependencies=[Depends(RateLimiter(times=5, minutes=1))],
            summary='Удаление задачи',
            response_description='Успешно удалена')
async def task_delete(user: dict = Depends(get_user_from_token),
                      id: int = Body(description='id задачи у которой необходимо удалить файл')):
    """
    ## Удаление задачи
        * id - id задачи которую необходимо удалить
    """
    # проверить наличие задачи с необходимым айди
    task_dict = await pg.tasks.get(id)
    if task_dict['email'] != user['email']:
        raise HTTPException(status_code=fastapi_status.HTTP_404_NOT_FOUND, detail='Такая задача не найдена')
    # удаление задачи в БД
    status = await pg.tasks.delete(id)
    if not status:
        raise HTTPException(status_code=fastapi_status.HTTP_500_INTERNAL_SERVER_ERROR)
    return Answer(status=True, id=id)


@router.patch('/status', status_code=fastapi_status.HTTP_200_OK,
            dependencies=[Depends(RateLimiter(times=5, minutes=1))],
            summary='Обновление статуса',
            response_description='Статус успешно обновлен')
async def task_set_status(user: dict = Depends(get_user_from_token), set_status: SetStatus = Body()) -> Answer:
    """
    ## Обновление статуса задачи
        * id - id задачи которую необходимо удалить
        * status - один из возможных статусов
    """
    task_dict = await pg.tasks.get(set_status.id)
    if task_dict['email'] != user['email']:
        raise HTTPException(status_code=fastapi_status.HTTP_404_NOT_FOUND, detail='Такая задача не найдена')
    # обновление статуса задачи в БД
    await pg.tasks.upd(user['email'], set_status.id, {'status': set_status.status})
    return Answer(status=True, id=set_status.id)


@router.post('/', deprecated=True)
async def task_update():
    pass
