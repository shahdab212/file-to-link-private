#!/bin/bash

nginx -g 'daemon off;' &

export PORT=8080
python bot_main.py
