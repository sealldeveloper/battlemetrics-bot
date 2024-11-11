#!/bin/bash

if [ ! -f "venv/bin/activate" ]; then
    echo " - Virtual environment not found. Running setup.sh..."
    ./setup.sh
fi

echo " - Activating virtual environment..."
source venv/bin/activate

echo " - Running main.py..."
python3 main.py
echo " - Deactivating virtual environment..."
deactivate