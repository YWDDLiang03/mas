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
    def open(cls, root: str | os.PathLike, **store_options) -> "Core":
        store = Store.open(root, **store_options)
        return cls(store, Journal(store), ArtifactStore(store))

    def close(self) -> None:
        self.store.close()

    def __enter__(self) -> "Core":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
