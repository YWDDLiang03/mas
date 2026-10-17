"""Windows first-use regression: initialize an empty store from another directory."""
from contextlib import closing
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pytest


@pytest.mark.skipif(sys.platform != "win32", reason="PowerShell launcher is Windows-specific")
@pytest.mark.parametrize("allow_operations", [False, True])
def test_launcher_initializes_an_empty_workspace_from_another_directory(tmp_path, allow_operations):
    source_root = Path(__file__).resolve().parents[1]
    workspace = tmp_path / "workspace"
    store = workspace / "store"
    # A tiny asset verifies asset-directory selection without requiring npm in pytest.
    assets = tmp_path / "client"
    assets.mkdir()
    (assets / "index.html").write_text("<html>launcher regression asset</html>", encoding="utf-8")
    environment = {key: value for key, value in os.environ.items() if not key.startswith("MAS_")}
    environment.update(MAS_CACHE=str(tmp_path / "cache"), MAS_WORKBENCH_ASSET_DIR=str(assets))
    with socket.socket() as available:
        available.bind(("127.0.0.1", 0))
        port = available.getsockname()[1]
    command = ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
               "-File", str(source_root / "scripts/start_workbench.ps1"),
               "-Store", str(store), "-Python", sys.executable, "-InitializeStore", "-NoBrowser",
               "-Port", str(port), "-Models", "config/examples/models.deepseek.toml",
               "-Config", "config/examples/mas.toml"]
    if allow_operations:
        command.append("-AllowOperations")
    base = f"http://127.0.0.1:{port}"
    output_path = tmp_path / "launcher.log"
    with output_path.open("wb") as output:
        process = subprocess.Popen(command, cwd=tmp_path, env=environment,
                                   stdout=output, stderr=subprocess.STDOUT)
        try:
            deadline = time.monotonic() + 20
            while True:
                assert process.poll() is None, output_path.read_text(encoding="utf-8", errors="replace")
                try:
                    with urlopen(base + "/", timeout=1) as response:
                        assert response.status == 200
                        page = response.read().decode("utf-8")
                    break
                except (URLError, TimeoutError):
                    if time.monotonic() > deadline:
                        pytest.fail(output_path.read_text(encoding="utf-8", errors="replace"))
                    time.sleep(.1)
            assert (store / "store.db").is_file()
            if allow_operations:
                assert "launcher regression asset" in page
                with urlopen(base + "/api/workbench/bootstrap", timeout=3) as response:
                    bootstrap = json.load(response)
                assert bootstrap["tasks"] == []
                assert bootstrap["libraries"] == []
                assert bootstrap["evidence_sources"] == []
                assert bootstrap["defaults"]["workers"] == 4
                assert bootstrap["operation_token"]
            else:
                request = Request(base + "/api/settings", data=b"{}", method="POST")
                with pytest.raises(HTTPError) as refused:
                    urlopen(request, timeout=3)
                assert refused.value.code == 405
        finally:
            if process.poll() is None:
                subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
            process.wait(timeout=10)
    with closing(sqlite3.connect((store / "store.db").resolve().as_uri() + "?mode=ro", uri=True)) as database:
        assert database.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 0
        assert database.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0] == 0
