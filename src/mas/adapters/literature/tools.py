"""Register the literature source tools with a broker (any task, any adapter).

Europe PMC and PubMed need nothing set up. Bookshelf answers once a book is synced,
uploads once a manifest declares readable documents; until then their tools report
`not_configured` and searches record them as unavailable rather than failed.
"""

from __future__ import annotations

from pathlib import Path

from .bookshelf import BookshelfLibrary, BookshelfReader, BookshelfSearch
from .europepmc import EuropePMCReader, EuropePMCSearch
from .mediawiki import MediaWikiReader, MediaWikiSearch
from .pubmed import PubMedSearch
from .uploads import UploadLibrary, UploadsReader, UploadsSearch


def register(broker, *, cache_dir: str | Path | None = None, upload_dir: str | Path | None = None) -> None:
    # Europe PMC first: without a named source, a search goes to the first tool that answers.
    library = BookshelfLibrary(cache_dir)
    uploads = UploadLibrary(upload_dir) if upload_dir else None
    for provider in (EuropePMCSearch(), PubMedSearch(), EuropePMCReader(),
                     BookshelfSearch(library), BookshelfReader(library),
                     MediaWikiSearch("wikibooks"), MediaWikiReader("wikibooks"),
                     MediaWikiSearch("wikipedia"), MediaWikiReader("wikipedia"),
                     UploadsSearch(uploads), UploadsReader(uploads)):
        broker.register(provider)
