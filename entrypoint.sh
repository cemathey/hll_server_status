#!/usr/bin/env bash
set -e
set -x

if [ ! -d "./config" ]
then
    echo "Creating config directory"
    mkdir ./config
fi

if [ ! -d "./logs" ]
then
    echo "Creating logs directory"
    mkdir ./logs
fi

if [ ! -d "./messages" ]
then
    echo "Creating messages directory"
    mkdir ./messages
fi

PYTHONPATH=. poetry run python -m hll_server_status.cli