#!/usr/bin/env bash

PIPENV_VENV_IN_PROJECT=1

python --version > /dev/null 2>&1
if [ $? != 0 ]
then
    echo Cannot find Python executable, make sure it is installed and added to your PATH.
    read -p "Press [Enter] to exit..."
    exit 0
fi

python -c "import pipenv" > /dev/null 2>&1
if [ $? != 0 ]
then
    python -m pip install --user pipenv
fi

if [ ! -d '.venv' ]
then
    pipenv --bare install
fi

rm panda.log
pipenv run python panda.py
