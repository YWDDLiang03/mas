import pytest

from mas.core.runtime import Core
from mas.core.store import Store


@pytest.fixture
def store(tmp_path):
    s = Store.open(tmp_path / "root")
    yield s
    s.close()


@pytest.fixture
def core(tmp_path):
    with Core.open(tmp_path / "root") as c:
        yield c
