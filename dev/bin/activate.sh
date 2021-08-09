#!/bin/bash

PROJECT_PATH=$(git rev-parse --show-toplevel)
VENV=${PROJECT_PATH}/.venv
REQUIREMENTS_FILE=${PROJECT_PATH}/dev/requirements-dev.txt

# check for python3
if ! command -v python3 &> /dev/null
then
    >&2 echo "ERROR: could  not find python3"
    exit 1
fi

# activate virtual environment
if [ -d "${VENV}" ] 
then
    echo "Found virtual environment ${VENV}"
    source ${VENV}/bin/activate
else
    echo "Create python virtual environment ${VENV}"
    python3 -m venv ${VENV}
    echo export PATH=${PROJECT_PATH}/dev/bin:\$PATH >> ${VENV}/bin/activate
    source ${VENV}/bin/activate
    pip3 install --upgrade pip setuptools wheel
    pip3 install -e ${PROJECT_PATH}
    pip3 install -r ${REQUIREMENTS_FILE}
fi
