import logging

# Создание логгера
logger = logging.getLogger("TasksAPI")
logger.setLevel(logging.DEBUG)

# Формат логов
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# Обработчик для записи в файл
file_handler = logging.FileHandler("main.log")
file_handler.setFormatter(formatter)

# Обработчик для вывода в консоль
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

# Добавление обработчиков к логгеру
logger.addHandler(file_handler)
logger.addHandler(console_handler)
