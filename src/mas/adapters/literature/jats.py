"""JATS full-text XML → title, metadata, and located passages.

Passage ids are stable locators: `abstract.p1`, `sec2.p3`, `sec2.1.p1`, `table1`,
`fig2.caption`. The reference list is not read.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import Any

_SPACE = re.compile(r"\s+")


def _text(element) -> str:
    return _SPACE.sub(" ", "".join(element.itertext())).strip() if element is not None else ""


def _table_text(wrap) -> str:
    parts = []
    label, caption = wrap.find("label"), wrap.find("caption")
    if label is not None:
        parts.append(_text(label))
    if caption is not None:
        parts.append(_text(caption))
    for row in wrap.iter("tr"):
        cells = [_text(cell) for cell in row if cell.tag in ("td", "th")]
        if any(cells):
            parts.append(" | ".join(cells))
    footer = wrap.find("table-wrap-foot")
    if footer is not None:
        parts.append(_text(footer))
    return "\n".join(p for p in parts if p)


_SKIP_SECTIONS = re.compile(r"^(\d+\.?\s*)?(references?|footnotes?|funding( statement)?|acknowledg(e)?ments?|"
                           r"author contributions?|conflicts? of interest|competing interests?|associated data|"
                           r"data availability( statement)?|abbreviations|supplementary (material|data))\b", re.I)


def _walk_sections(section, path: list[str], prefix: str, passages: list[dict[str, Any]]) -> None:
    title = _text(section.find("title"))
    if title and _SKIP_SECTIONS.match(title):
        return
    here = path + ([title] if title else [])
    paragraph_no, child_no = 0, 0
    for child in section:
        if child.tag == "p":
            text = _text(child)
            if text:
                paragraph_no += 1
                passages.append({"passage_id": f"{prefix}.p{paragraph_no}", "kind": "paragraph",
                                 "section_path": here, "text": text})
        elif child.tag == "sec":
            child_no += 1
            _walk_sections(child, here, f"{prefix}.{child_no}", passages)
        elif child.tag in ("list", "def-list", "disp-quote", "boxed-text", "statement"):
            text = _text(child)
            if text:
                paragraph_no += 1
                passages.append({"passage_id": f"{prefix}.p{paragraph_no}", "kind": "paragraph",
                                 "section_path": here, "text": text})


def parse(xml_text: str) -> dict[str, Any]:
    root = ET.fromstring(xml_text)
    meta = root.find("front/article-meta")
    ids = {}
    if meta is not None:
        for article_id in meta.findall("article-id"):
            ids[article_id.get("pub-id-type")] = (article_id.text or "").strip()
    title = _text(root.find(".//title-group/article-title"))
    year = ""
    if meta is not None:
        for date in meta.findall("pub-date"):
            year = _text(date.find("year")) or year
    passages: list[dict[str, Any]] = [{"passage_id": "title", "kind": "title", "section_path": [], "text": title}] if title else []
    abstract = root.find(".//article-meta/abstract")
    if abstract is not None:
        paras = abstract.findall(".//p") or [abstract]
        for index, para in enumerate(paras, 1):
            text = _text(para)
            if text:
                passages.append({"passage_id": f"abstract.p{index}", "kind": "abstract", "section_path": ["Abstract"], "text": text})
    body = root.find("body")
    if body is not None:
        section_no, loose_no = 0, 0
        for child in body:
            if child.tag == "sec":
                section_no += 1
                _walk_sections(child, [], f"sec{section_no}", passages)
            elif child.tag == "p":
                loose_no += 1
                text = _text(child)
                if text:
                    passages.append({"passage_id": f"body.p{loose_no}", "kind": "paragraph", "section_path": [], "text": text})
    for index, wrap in enumerate(root.iter("table-wrap"), 1):
        text = _table_text(wrap)
        if text:
            passages.append({"passage_id": f"table{index}", "kind": "table", "section_path": ["Tables"], "text": text})
    for index, fig in enumerate(root.iter("fig"), 1):
        text = _text(fig.find("caption"))
        if text:
            passages.append({"passage_id": f"fig{index}.caption", "kind": "figure_caption", "section_path": ["Figures"], "text": text})
    license_el = root.find(".//permissions/license")
    return {"title": title, "year": year, "identifiers": ids, "passages": passages,
            "license": (license_el.get("{http://www.w3.org/1999/xlink}href") if license_el is not None else None)
            or _text(license_el)[:200] or None}


_TAG = re.compile(r"<[^>]+>")


def strip_html(text: str | None) -> str:
    if not text:
        return ""
    return _SPACE.sub(" ", _TAG.sub(" ", text)).strip()


def abstract_passages(abstract_html: str | None, title: str | None) -> list[dict[str, Any]]:
    """Passages for an abstract-only reading; headings like <h4>Background</h4> split paragraphs."""
    passages = [{"passage_id": "title", "kind": "title", "section_path": [], "text": title.strip()}] if title else []
    if not abstract_html:
        return passages
    chunks = [c for c in re.split(r"<h4>|</h4>", abstract_html) if c.strip()]
    text_chunks = []
    heading = None
    for chunk in chunks:
        clean = strip_html(chunk)
        if len(clean) < 40 and not clean.endswith("."):
            heading = clean
            continue
        text_chunks.append((heading, clean))
        heading = None
    for index, (heading, text) in enumerate(text_chunks or [(None, strip_html(abstract_html))], 1):
        passages.append({"passage_id": f"abstract.p{index}", "kind": "abstract",
                         "section_path": ["Abstract"] + ([heading] if heading else []), "text": text})
    return passages
