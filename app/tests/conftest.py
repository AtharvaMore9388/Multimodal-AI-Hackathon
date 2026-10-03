import pytest


def pytest_configure(config):
    backend_opt = config.getoption("anyio_backend", None)
    backends_opt = getattr(config.option, "anyio_backends", None)
    if backends_opt is not None:
        try:
            config.option.anyio_backends = ["asyncio"]
        except Exception:
            pass


@pytest.fixture
def anyio_backend():
    return "asyncio"
