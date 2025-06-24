FROM python:3.12

WORKDIR /app

COPY ./requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY . /app

CMD ["fastapi", "run", "main.py", "--port", "80"]

EXPOSE 80
