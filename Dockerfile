FROM ubuntu:22.04

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    git \
    wget \
    libgmp-dev \
    libzmq3-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN wget https://github.com/leanprover/lean4/releases/download/nightly-2022-07-21/lean-4.0.0-nightly-2022-07-21-ubuntu.tar.gz \
    && tar -xzf lean-4.0.0-nightly-2022-07-21-ubuntu.tar.gz \
    && cp lean-4.0.0-nightly-2022-07-21-ubuntu/bin/lean /usr/local/bin/lean \
    && cp lean-4.0.0-nightly-2022-07-21-ubuntu/bin/leanc /usr/local/bin/leanc \
    && rm -rf lean-4.0.0-nightly-2022-07-21-ubuntu*

RUN pip3 install pyzmq numpy jsonschema

WORKDIR /app
COPY . /app

RUN cd lean && lake build

EXPOSE 5555

CMD ["python3", "python/src/server.py"]
