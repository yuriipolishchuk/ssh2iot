FROM python:3.8.2

ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install --no-cache-dir boto3

COPY bin/localproxy /usr/local/bin/localproxy

COPY src/ssh2iot.py .

ENTRYPOINT ["python", "/app/ssh2iot.py"]
