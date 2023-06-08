FROM python:3.10.10-slim

COPY requirements.txt /tmp
#ADD https://anaconda.org/conda-forge/openh264/2.1.1/download/linux-64/openh264-2.1.1-h780b84a_0.tar.bz2 /tmp

WORKDIR /usr

RUN apt update && apt install -y --no-install-recommends --no-install-suggests \
    build-essential curl git && pip install -r /tmp/requirements.txt && \
    curl -JOLk https://anaconda.org/conda-forge/openh264/2.1.1/download/linux-64/openh264-2.1.1-h780b84a_0.tar.bz2 /tmp && \
    pip install --local /tmp/linux-64/openh264-2.1.1-h780b84a_0.tar.bz2 && \
    apt purge -y --autoremove build-essential curl git && \
    rm -rf /var/lib/apt/lists/*

RUN addgroup --gid 1000 projectp && \
    adduser --uid 1000 --gid 1000 --home /opt/projectp --shell /bin/bash \
            --disabled-password --gecos "" projectp

USER projectp:projectp

WORKDIR /opt/projectp

COPY --chown=projectp:projectp main.py ./
COPY --chown=projectp:projectp models ./models/

ENTRYPOINT ["/usr/local/bin/python"]

CMD ["/opt/projectp/main.py"]
