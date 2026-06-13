"""
Shared pytest fixtures for the Jorres Apps test suites.

The `live_server` fixture boots the real WSGI stack (lazy dispatcher +
middleware) on a free localhost port in a background thread, so the
Playwright e2e layer can drive the apps in a real browser. It is only
instantiated when an e2e test asks for it — the fast hermetic suites
(`test_smoke.py`, `test_functional.py`) never start a server.
"""
import os
import socket
import sys
import threading
import time

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def _free_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('127.0.0.1', 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture(scope='session')
def live_server():
    """Start the full WSGI app on a background thread; yield the base URL."""
    from werkzeug.serving import make_server
    import app as launcher

    port = _free_port()
    server = make_server('127.0.0.1', port, launcher.app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    base = f'http://127.0.0.1:{port}'
    # Wait until the server answers before handing the URL to tests
    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            with socket.create_connection(('127.0.0.1', port), timeout=0.5):
                break
        except OSError:
            time.sleep(0.1)
    else:
        server.shutdown()
        raise RuntimeError('live_server did not start in time')

    yield base

    server.shutdown()
    thread.join(timeout=5)


@pytest.fixture(scope='session')
def base_url(live_server):
    """pytest-playwright reads `base_url`; point it at our live server."""
    return live_server
