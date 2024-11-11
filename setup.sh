#!/bin/bash

echo " - Setting up venv..."
python3 -m venv venv
echo " - Entering venv..."
source venv/bin/activate
echo " - Installing requirements..."
pip3 install -r requirements.txt
echo " - All done!"
deactivate