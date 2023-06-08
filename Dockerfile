FROM python:3.10.10-slim

COPY requirements.txt /tmp

WORKDIR /usr

RUN apt update && apt install -y --no-install-recommends --no-install-suggests \
    build-essential git ffmpeg python3-opencv x264 && \
    pip install -r /tmp/requirements.txt && \
    apt purge --autoremove build-essential git && rm -rf /var/lib/apt/lists/*

RUN addgroup --gid 1000 projectp && \
    adduser --uid 1000 --gid 1000 --home /opt/projectp --shell /bin/bash \
            --disabled-password --gecos "" projectp

USER projectp:projectp

WORKDIR /opt/projectp

COPY --chown=projectp:projectp main.py ./
COPY --chown=projectp:projectp models ./models/

ENTRYPOINT ["/usr/local/bin/python"]

CMD ["/opt/projectp/main.py"]
