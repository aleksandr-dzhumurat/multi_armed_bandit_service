FROM python:3.10

ENV PYTHONPATH=/srv \
    # Keeps Python from generating .pyc files in the container
    PYTHONDONTWRITEBYTECODE=1 \
    # Turns off buffering for easier container logging
    PYTHONUNBUFFERED=1

WORKDIR /srv/

COPY requirements.txt /srv/

RUN \
    apt-get update && python3.10 -m pip install --upgrade pip && \
    python3.10 -m pip install --no-cache -r requirements.txt

COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENTRYPOINT ["docker-entrypoint.sh"]