#!/bin/bash

# Wait a few seconds to ensure network and display are ready
sleep 5

# Go to project folder
cd /home/jjm/jjm

# Activate virtual environment
source venv/bin/activate

# Run your Python script
python3 main.py
