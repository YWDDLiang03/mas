"""The open core: one store root with its journal and artifact store."""

from __future__ import annotations

import os
from dataclasses import dataclass

from .artifacts import ArtifactStore
from .journal import Journal
from .store import Store


@dataclass
class Core:
    store: Store
    journal: Journal
    artifacts: ArtifactStore

    @classmethod
    def open(cls, root: str | os.PathLike, *, read_only: bool = False, **store_options) -> "Core":
        """Open a store root. `read_only=True` takes no lock, so it opens a root a host already holds,
        and refuses every write with `StoreError("read_only", ...)`."""
        store = Store.open(root, read_only=read_only, **store_options)
        return cls(store, Journal(store), ArtifactStore(store))

    @property
    def read_only(self) -> bool:
        return self.store.read_only

    def close(self) -> None:
        self.store.close()

    def __enter__(self) -> "Core":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
