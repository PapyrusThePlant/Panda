#!/usr/bin/env bash

# Check git version
if ! git --version > /dev/null 2>&1
then
  echo Cannot find Git executable, make sure it is installed and added to your PATH.
  read -rp "Press [Enter] to exit..."
  exit 0
fi

# Check python version
python_version=$(python3 --version)
if [[ -z "$python_version" ]]
then
  echo Cannot find Python3 executable, make sure it is installed and added to your PATH.
  read -rp "Press [Enter] to exit..."
  exit 0
elif printf '%s\n%s' "$python_version" "Python 3.6" | sort -CV
then
  echo Python 3.6 or newer required. "$python_version" found.
  read -rp "Press [Enter] to exit..."
  exit 0
fi

# Create the virtual env if necessary
if [[ ! -d '.venv' ]]
then
    python3 -m venv .venv
fi

# Activate and update the virtual env
source .venv/bin/activate
pip install -Ur requirements.txt

# Check libopus
if ! python3 -c "exit(__import__('discord').opus.is_loaded())" > /dev/null 2>&1
then
  echo Cannot find libopus on your system, make sure it is installed.
  read -rp "Press [Enter] to exit..."
  exit 0
fi

rm panda.log
python3 panda.py

# Deactivate the virtual env
deactivate
