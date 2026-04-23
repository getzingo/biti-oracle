#!/bin/bash
# Author: getzi
# Usage: ./run-demo.sh

if ! [ -d "venv" ]; then
  echo 'Virtual environment not found!'
  echo 'Please run `python3 -m venv venv` first.'
  echo 'Exiting ...'
  exit 1
fi

export SDL_VIDEODRIVER=kmsdrm
source sensor_env/bin/activate
python3 demo.py