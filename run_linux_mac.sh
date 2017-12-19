#!/usr/bin/env bash

PIPENV_VENV_IN_PROJECT=1

python3 --version > /dev/null 2>&1
if [ $? != 0 ]
then
    echo Cannot find Python3 executable, make sure it is installed and added to your PATH.
    read -p "Press [Enter] to exit..."
    exit 0
fi

python3 -c "import pipenv" > /dev/null 2>&1
if [ $? != 0 ]
then
    python3 -m pip install --user pipenv
fi

if [ ! -d '.venv' ]
then
    pipenv --bare install
fi

rm panda.log
pipenv run python3 panda.py
