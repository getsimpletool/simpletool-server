#!/bin/bash

# Set the Python path to include the current directory
export PYTHONPATH="$PYTHONPATH:$(pwd)"
export PYTHONPATH="$PYTHONPATH:/app"

# Run the server (uvicorn)
# uvicorn main:fastapi --reload --host 0.0.0.0 --port 8000

# Run the server using the __main__ module
python -m mcpo_simple_server --host 0.0.0.0 --port 8000 --reload