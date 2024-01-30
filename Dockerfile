# Используйте официальный образ Python 3.8
FROM python:3.8

# Устанавливает рабочий каталог в /app
WORKDIR /app

# Устанавливает переменные окружения
ENV PYTHONUNBUFFERED 1

# Копирует только requirements.txt и устанавливает зависимости
COPY requirements.txt /app/
RUN pip install -r requirements.txt
# Проверить и установить Celery, если он не указан в requirements.txt
RUN pip freeze | grep Celery || pip install celery
RUN apt-get update && apt-get install -y wget gnupg \
    && wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list' \
    && apt-get update \
    && apt-get install -y google-chrome-stable

RUN apt-get install -y chromium-driver
RUN pip install lxml
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver
RUN pip install gunicorn
RUN apt-get update && apt-get install -y xvfb

# Копирует оставшиеся файлы проекта в контейнер
COPY . /app/

# Запускает Gunicorn
CMD ["gunicorn", "-b", "0.0.0.0:8000", "fintracker_parser.wsgi:application", "--timeout", "120"]

# CMD ["celery", "-A", "test_backend", "worker", "-l", "info"]

