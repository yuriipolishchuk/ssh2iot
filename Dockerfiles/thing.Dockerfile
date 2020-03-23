FROM python:3.8.2

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# install and configure sshd and supervisor
RUN apt update && \
    apt install -y openssh-server supervisor && \
    mkdir -p /run/sshd && \
    sed -i 's/#ListenAddress 0.0.0.0/ListenAddress 127.0.0.1/' /etc/ssh/sshd_config && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY bin/localproxy /usr/local/bin/localproxy

COPY supervisor.conf /etc/supervisor/conf.d/supervisor.conf
COPY authorized_keys /root/.ssh/authorized_keys

COPY src/tunnel-agent.py .

ENTRYPOINT /usr/bin/supervisord
