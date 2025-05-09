
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

# Create test environment directory if it doesn't exist
if not DST.parent.exists():
    DST.mkdir(parents=True, exist_ok=True)

# Add test environment to PYTHONPATH
os.environ['PYTHONPATH'] = os.environ.get('PYTHONPATH', '') + ':/app'
os.environ['PYTHONPATH'] = os.environ.get('PYTHONPATH', '') + ':' + str(DST.parent)


def pytest_addoption(parser):
    parser.addoption(
        '--clean', action='store_true',
        help=f'Start a clean server instance in {DST} on port 9999'
    )


@pytest.fixture(scope='session')
def server_url(request):
    """
    Provide the base URL for tests.

    If --clean is used, spin up a fresh uvicorn process.
    Otherwise, use an existing server instance if available.
    """
    clean = request.config.getoption('--clean')

    # If DST not exists, use it
    if not DST.exists():
        print(f"Creating folder {DST}")
        os.makedirs(DST, exist_ok=True)

    # If clean option is specified, always create a fresh copy
    if clean:
        print(f"Setting up clean test environment in {DST}")
        # Remove existing directory if it exists
        if DST.exists():
            shutil.rmtree(DST)
        # Copy source files to test environment
        shutil.copytree(SRC, DST)
        # Create empty data directory
        shutil.rmtree(DST / 'data', ignore_errors=True)
        os.makedirs(DST / 'data', exist_ok=True)
        # Remove .env file to ensure clean configuration
        (DST / '.env').unlink(missing_ok=True)
    else:
        print(f"Using existing test environment in {DST}")
        # If directory doesn't exist, create it
        if not DST.exists():
            print("Test environment doesn't exist. Creating it now...")
            shutil.copytree(SRC, DST)
            os.makedirs(DST / 'data', exist_ok=True)

    # Start uvicorn server
    proc = subprocess.Popen([
        sys.executable, '-m', 'uvicorn', 'main:fastapi',
        '--host', '0.0.0.0', '--port', '9999'
    ], cwd=str(DST), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Wait for server to be ready
    print("Waiting for test server to start...")
    for _ in range(30):
        try:
            r = httpx.get(CLEAN_URL + "/health", timeout=1)
            if r.status_code == 200:
                print("Test server started successfully")
                break
        except Exception:
            time.sleep(1)
    else:
        proc.terminate()
        pytest.exit("Test server did not start in time")

    yield CLEAN_URL

    # Teardown - stop the server but don't remove files if use_existing
    print("Stopping test server...")
    proc.terminate()
    proc.wait(timeout=10)


# Add fixture to obtain and return admin access token for authenticated tests
@pytest.fixture(scope='session')
def admin_auth_token(server_url):
    r = httpx.get(f"{server_url}/user/me")
    assert r.status_code == 401
    with httpx.Client() as client:
        response = client.post(
            server_url + "/user/login", json={"username": "admin", "password": "admin"}
        )
    print(response)
    assert response.status_code == 200
    return response.json()["access_token"]
