import pytest

from mas.core.store import Store


@pytest.fixture
def store(tmp_path):
    s = Store.open(tmp_path / "root")
    yield s
    s.close()
