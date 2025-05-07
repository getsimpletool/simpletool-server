
import os
import sys
import shutil
import subprocess
import time
import pytest
import httpx
from pathlib import Path


# Paths for clean server copy
# Copy from project root src/server
SRC = Path(__file__).parent.parent.parent / 'src' / 'mcpo_simple_server'
DST = Path('/tmp/testing/mcpo_simple_server')
CLEAN_URL = 'http://localhost:9999'

# Check if DST exist
if not DST.exists():
    DST.mkdir(parents=True, exist_ok=True)

os.environ['PYTHONPATH'] = f"{os.environ.get('PYTHONPATH', '')}:/app"
os.environ['PYTHONPATH'] = f"{os.environ.get('PYTHONPATH', '')}:{DST.parent}"


def pytest_addoption(parser):
    parser.addoption(
        '--clean', action='store_true',
        help=f'Start a clean server instance in {DST} on port 9999'
    )


@pytest.fixture(scope='session')
def server_url(request):
    """
    Provide the base URL for tests. If --clean is used, spin up a fresh uvicorn process.
    """
    clean = request.config.getoption('--clean')
    if clean:
        # copy source
        if DST.exists():
            shutil.rmtree(DST)
        shutil.copytree(SRC, DST)
        # to have a clean config, remove config files in DST/data folder
        shutil.rmtree(DST / 'data', ignore_errors=True)
        os.makedirs(DST / 'data', exist_ok=True)
        # remove also .env file
        (DST / '.env').unlink(missing_ok=True)
        # start uvicorn
        proc = subprocess.Popen([
            sys.executable, '-m', 'uvicorn', 'main:fastapi',
            '--host', '0.0.0.0', '--port', '9999'
        ], cwd=str(DST), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # wait for /health
        for _ in range(30):
            try:
                r = httpx.get(f"{CLEAN_URL}/health", timeout=1)
                if r.status_code == 200:
                    break
            except Exception:
                # print(f"Response: {r.status_code}")
                time.sleep(1)
        else:
            proc.terminate()
            pytest.exit("Clean server did not start in time")
        yield CLEAN_URL
        # teardown
        proc.terminate()
        proc.wait(timeout=10)
        shutil.rmtree(DST, ignore_errors=True)
    else:
        yield os.getenv('MCP_SERVER_URL', 'http://localhost:8000')


# Add fixture to obtain and return admin access token for authenticated tests
@pytest.fixture(scope='session')
def auth_token(server_url):
    with httpx.Client() as client:
        response = client.post(
            f"{server_url}/user/login", json={"username": "admin", "password": "admin"}
        )
    assert response.status_code == 200
    return response.json()["access_token"]
