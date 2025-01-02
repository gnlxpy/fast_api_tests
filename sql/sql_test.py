from dotenv import load_dotenv
import psycopg2
import os

load_dotenv()

db_config = {
    "dbname": "postgres",
    "user": os.getenv('PG_USR'),
    "password": os.getenv('PG_PSW'),
    "host": os.getenv('PG_IP'),  # или IP-адрес сервера
    "port": "5432",       # стандартный порт PostgreSQL
}

try:
    # Подключение к базе данных
    connection = psycopg2.connect(**db_config)
    cursor = connection.cursor()

    # Пример: чтение данных
    select_query = """
    SELECT
      margin_ozon.nmid,
      MIN(art.item_name),
      MIN(margin_ozon.llc),
      ROUND(CAST(AVG(margin_ozon.margin_after_spp) AS numeric),2) AS margin_avg
    FROM
      margin_ozon
      JOIN art ON margin_ozon.nmid = art.sku
    WHERE
      margin_ozon.date > '2024-12-30'
      AND margin_ozon.llc = 'vosne'
    GROUP BY
      margin_ozon.nmid
    ORDER BY
      margin_avg DESC
    """
    # select_query = """
    # DESCRIBE margin_ozon;
    # """
    cursor.execute(select_query)
    rows = cursor.fetchall()
    n = 0
    for row in rows:
        n += 1
        print(row)
    print(f'rows = {n}')
except psycopg2.Error as e:
    print(f"Ошибка при работе с PostgreSQL: {e}")

finally:
    # Закрытие соединения
    if cursor:
        cursor.close()
    if connection:
        connection.close()
    print("Соединение с PostgreSQL закрыто.")
