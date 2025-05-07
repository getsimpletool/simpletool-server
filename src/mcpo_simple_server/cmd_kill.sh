#!/bin/bash

# Kill any running simpletool server processes
ps aux | grep "gunicorn" | grep "simpletool" | grep -v grep | awk '{print $2}' | xargs -r kill -9
ps aux | grep "python3 -m server" | grep -v grep | awk '{print $2}' | xargs -r kill -9

# Remove stale PID file
rm -f /var/run/simpletool/gunicorn.pid

# Kill any process using port 8000
lsof -ti :8000 | xargs -r kill -9

echo "All SimpleTool Server processes killed"
