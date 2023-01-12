# syntax=docker/dockerfile:1
FROM python:3.11-slim-buster

RUN apt update -y && apt upgrade --no-install-recommends -y
RUN apt install curl -y

WORKDIR /code

COPY . .

RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="/root/.local/bin:$PATH"
RUN poetry install
CMD poetry run python ./hll_server_status/cli.py