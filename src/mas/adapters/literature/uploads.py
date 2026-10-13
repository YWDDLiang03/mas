"""Documents the user supplies: a folder plus a manifest that declares each document's rights.

    UPLOAD_DIR/manifest.toml
        [[document]]
        file = "pk-handbook-ch3.pdf"
        title = "Oral absorption of kinase inhibitors"
        year = 2021
        authors = "A. Author"
        license = "licensed copy for internal research"
        llm_ingestion_permitted = true

A file is searched and read only when its manifest entry says a language model may read
it; anything else in the folder is ignored and reported by `mas sources check`. Supported
formats: PDF (via `pdftotext`, if installed), plain text and Markdown, HTML, and JATS or
BITS XML. Search is local keyword scoring over the parsed passages.
"""

from __future__ import annotations

import hashlib
import math
import re
import shutil
import subprocess
import tomllib
from pathlib import Path
from typing import Any

from mas.core.broker import ProviderResponse, ToolAbsent, ToolContract, ToolError

from . import jats, textparse

MANIFEST = "manifest.toml"
FORMATS = {".pdf", ".txt", ".md", ".markdown", ".html", ".htm", ".xml", ".nxml"}
_WORD = re.compile(r"[a-z0-9][a-z0-9\-]+")
_STOP = {"and", "or", "not", "the", "of", "in", "for", "with", "to", "a", "an", "on", "by", "as", "is", "are"}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_file(path: Path, title: str | None = None) -> list[dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        tool = shutil.which("pdftotext")
        if tool is None:
            raise ToolAbsent("not_installed", "reading PDF uploads needs `pdftotext` (poppler-utils)")
        out = subprocess.run([tool, "-enc", "UTF-8", str(path), "-"], capture_output=True, timeout=300)
        if out.returncode != 0:
            raise ToolError("parse_failed", f"pdftotext failed on {path.name}", retryable=False)
        text = out.stdout.decode("utf-8", "replace").replace("\f", "\n\n")
        # pdftotext breaks lines inside paragraphs; join lines that do not end a sentence
        text = re.sub(r"(?<![.:;!?])\n(?!\n)", " ", text)
        return textparse.text_passages(text, title=title)
    raw = path.read_text(encoding="utf-8", errors="replace")
    if suffix in (".html", ".htm"):
        return textparse.html_passages(raw, title=title)
    if suffix in (".xml", ".nxml"):
        parsed = jats.parse_bits(raw) if "<book-part" in raw[:4000] else jats.parse(raw)
        return parsed["passages"]
    return textparse.text_passages(raw, title=title)


class UploadLibrary:
    def __init__(self, directory: str | Path):
        self.root = Path(directory)
        self._parsed: dict[str, list[dict[str, Any]]] = {}

    def manifest(self) -> list[dict[str, Any]]:
        path = self.root / MANIFEST
        if not path.exists():
            return []
        entries = tomllib.loads(path.read_text(encoding="utf-8")).get("document", [])
        return [dict(e) for e in entries if isinstance(e, dict) and e.get("file")]

    def check(self) -> dict[str, list[str]]:
        """Which files are readable, which are refused, and why."""
        declared = {e["file"]: e for e in self.manifest()}
        report = {"readable": [], "refused": [], "missing": []}
        for name, entry in sorted(declared.items()):
            if not (self.root / name).exists():
                report["missing"].append(name)
            elif entry.get("llm_ingestion_permitted") is not True or not entry.get("license"):
                report["refused"].append(f"{name}: manifest must declare a licence and llm_ingestion_permitted = true")
            elif Path(name).suffix.lower() not in FORMATS:
                report["refused"].append(f"{name}: unsupported format")
            else:
                report["readable"].append(name)
        if self.root.exists():
            for path in sorted(self.root.iterdir()):
                if path.is_file() and path.name != MANIFEST and path.name not in declared:
                    report["refused"].append(f"{path.name}: not declared in {MANIFEST}")
        return report

    def documents(self) -> list[dict[str, Any]]:
        readable = set(self.check()["readable"])
        return [e for e in self.manifest() if e["file"] in readable]

    def passages(self, entry: dict[str, Any]) -> list[dict[str, Any]]:
        path = self.root / entry["file"]
        digest = _sha(path)
        if digest not in self._parsed:
            self._parsed[digest] = parse_file(path, entry.get("title") or path.stem)
        return self._parsed[digest]

    def hit(self, entry: dict[str, Any], rank: int, lead: str) -> dict[str, Any]:
        digest = _sha(self.root / entry["file"])
        return {"source": "uploads", "identifiers": [{"scheme": "sha256", "value": digest[:16]}], "upload_file": entry["file"],
                "sha256": digest, "title": entry.get("title") or Path(entry["file"]).stem, "authors": entry.get("authors", ""),
                "journal": entry.get("container", "uploaded document"), "year": str(entry.get("year", "")),
                "first_publication_date": entry.get("date"), "is_open_access": True, "in_epmc": False,
                "pub_types": [entry.get("kind", "user supplied document")], "is_preprint": False,
                "is_review": bool(entry.get("is_review", False)), "abstract_html": lead, "license": entry.get("license"),
                "best_rank": rank}


def _terms(query: str) -> list[str]:
    return [w for w in _WORD.findall(query.lower()) if w not in _STOP]


class UploadsSearch:
    contract = ToolContract(
        tool_id="tool_literature_uploads_search", capability="literature_retrieval", capability_kind="source_retrieval",
        question_kinds=("search",), contract_version="1", implementation_version="uploads-keyword-1",
        purpose_statement="Find user-supplied documents relevant to a query", evidence_kind_produced="user_supplied_document",
        claim_strength_ceiling="curated", required_inputs=("query",), license_id="declared per document")

    def __init__(self, library: UploadLibrary | None):
        self.library = library

    def invoke(self, question_kind: str, inputs: dict[str, Any]) -> ProviderResponse:
        if self.library is None or not self.library.documents():
            raise ToolAbsent("not_configured", "no readable uploaded documents (see `mas sources check`)")
        terms = _terms(inputs["query"])
        scored = []
        documents = self.library.documents()
        frequency = {t: sum(any(t in p["text"].lower() for p in self.library.passages(e)) for e in documents) for t in terms}
        for entry in documents:
            passages = self.library.passages(entry)
            text = " ".join(p["text"].lower() for p in passages)
            score = sum(math.log(1 + text.count(t)) * math.log(1 + len(documents) / (1 + frequency[t])) for t in terms)
            if score > 0:
                lead = " ".join(p["text"] for p in passages if p["kind"] in ("abstract", "paragraph"))[:1500]
                scored.append((score, entry, lead))
        scored.sort(key=lambda s: -s[0])
        limit = max(1, int(inputs.get("limit", 10)))
        hits = [self.library.hit(entry, rank, lead) for rank, (_, entry, lead) in enumerate(scored[:limit])]
        return ProviderResponse(values=[{"name": "search_hit", "value": h, "value_kind": "curated"} for h in hits],
                                records=[{"query": inputs["query"], "returned": len(hits)}], data_version="uploads")


class UploadsReader:
    contract = ToolContract(
        tool_id="tool_literature_uploads_reader", capability="document_reading", capability_kind="document_reading",
        question_kinds=("read",), contract_version="1", implementation_version="uploads-parse-1",
        purpose_statement="Read a user-supplied document with located passages",
        evidence_kind_produced="user_supplied_document", claim_strength_ceiling="curated",
        license_id="declared per document")

    def __init__(self, library: UploadLibrary | None):
        self.library = library

    def invoke(self, question_kind: str, inputs: dict[str, Any]) -> ProviderResponse:
        hit = inputs.get("hit") or {}
        entry = next((e for e in (self.library.documents() if self.library else []) if e["file"] == hit.get("upload_file")), None)
        if entry is None:
            raise ToolAbsent("declined_by_policy", f"{hit.get('upload_file')} is not a readable declared upload")
        if _sha(self.library.root / entry["file"]) != hit.get("sha256"):
            raise ToolError("input_invalid", f"{entry['file']} changed since it was found", retryable=False)
        document = {"title": hit["title"], "year": hit.get("year"), "identifiers": {"sha256": hit["sha256"], "file": entry["file"]},
                    "passages": self.library.passages(entry), "license": entry.get("license"),
                    "access_state": "full_text_available", "reading_depth": "full_text",
                    "source_hit": {k: hit.get(k) for k in ("title", "authors", "journal", "year", "pub_types")}}
        return ProviderResponse(values=[{"name": "document", "value": document, "value_kind": "curated"}],
                                data_version=f"upload:{hit['sha256'][:16]}", upstream_refs=[f"upload:{entry['file']}"])
