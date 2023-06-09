FROM continuumio/miniconda3:23.3.1-0

COPY requirements.txt /tmp

WORKDIR /usr

RUN apt update && apt install -y --no-install-recommends --no-install-suggests \
    build-essential git libgl1-mesa-glx && \
    conda install -y -c conda-forge filetype matplotlib onnxruntime openh264 \
    pandas py-opencv python-telegram-bot tqdm && \
    pip install -r /tmp/requirements.txt ensemble-boxes==1.0.9 && \
    apt purge -y --autoremove build-essential git && \
    rm -rf /var/lib/apt/lists/*

RUN addgroup --gid 1000 projectp && \
    adduser --uid 1000 --gid 1000 --home /opt/projectp --shell /bin/bash \
            --disabled-password --gecos "" projectp

USER projectp:projectp

WORKDIR /opt/projectp

COPY --chown=projectp:projectp main.py ./
COPY --chown=projectp:projectp models ./models/

ENTRYPOINT ["/opt/conda/bin/python"]

CMD ["/opt/projectp/main.py"]
