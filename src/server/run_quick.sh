#!/bin/bash

# Set the Python path to include the current directory
export PYTHONPATH="$PYTHONPATH:$(pwd)"
export PYTHONPATH="$PYTHONPATH:/app"

# Run the server
uvicorn main:fastapi --reload --host 0.0.0.0 --port 8000