FROM docker.io/library/python:3.13-alpine

RUN pip install --no-cache-dir requests redis

COPY ./src/poller.py /app/poller.py

USER 1001
WORKDIR /app

CMD ["python", "-u", "/app/poller.py"]
