"""HTML and plain text → located passages, in the same shape as the JATS parser.

Passage ids are stable within one fetched revision: `s<section>.p<paragraph>`, with the
lead (text before the first heading) as `lead.p<n>` and kind `abstract`, so passage
selection always keeps it, as it keeps a paper's abstract.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import Any

_SPACE = re.compile(r"\s+")
_HEADINGS = {"h1": 1, "h2": 1, "h3": 2, "h4": 3, "h5": 4, "h6": 5}
_BLOCKS = {"p", "li", "dd", "blockquote", "td", "th", "caption"}
_SKIP_TAGS = {"script", "style", "sup", "noscript", "math", "figure", "nav"}
_SKIP_CLASSES = re.compile(r"\b(reference|reflist|references|navbox|infobox|toc|mw-editsection|metadata|"
                           r"hatnote|sidebar|thumb|gallery|noprint|mw-empty-elt|citation|catlinks)\b")
_BACK_MATTER = re.compile(r"^(references?|notes|footnotes|see also|external links|further reading|bibliography|"
                          r"sources|citations)$", re.I)


class _Collector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.path: list[str] = []
        self.skip_depth = 0
        self.stack: list[tuple[str, bool]] = []
        self.heading_level: int | None = None
        self.heading_text: list[str] = []
        self.block: list[str] | None = None
        self.block_depth = 0
        self.items: list[tuple[list[str], str]] = []   # (section path, text)
        self.back_matter = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        skip = tag in _SKIP_TAGS or bool(_SKIP_CLASSES.search(attrs.get("class") or ""))
        if tag in ("br", "img", "hr", "meta", "link", "input", "wbr"):
            return
        self.stack.append((tag, skip))
        if skip:
            self.skip_depth += 1
            return
        if self.skip_depth:
            return
        if tag in _HEADINGS:
            self._flush()
            self.heading_level, self.heading_text = _HEADINGS[tag], []
        elif tag in _BLOCKS and self.block is None:
            self.block, self.block_depth = [], len(self.stack)

    def handle_endtag(self, tag):
        while self.stack:
            open_tag, skip = self.stack.pop()
            if skip:
                self.skip_depth -= 1
            if not self.skip_depth and open_tag in _HEADINGS and self.heading_level is not None:
                title = _SPACE.sub(" ", "".join(self.heading_text)).strip()
                level = self.heading_level
                self.path = self.path[: level - 1] + [title] if title else self.path
                self.back_matter = bool(_BACK_MATTER.match(title)) if level == 1 else self.back_matter
                self.heading_level = None
            if self.block is not None and len(self.stack) < self.block_depth:
                self._flush()
            if open_tag == tag:
                break

    def handle_data(self, data):
        if self.skip_depth:
            return
        if self.heading_level is not None:
            self.heading_text.append(data)
        elif self.block is not None:
            self.block.append(data)

    def _flush(self):
        if self.block is not None:
            text = _SPACE.sub(" ", "".join(self.block)).strip()
            if text and not self.back_matter:
                self.items.append((list(self.path), text))
        self.block = None


def _number(items: list[tuple[list[str], str]], min_chars: int) -> list[dict[str, Any]]:
    passages, section_ids, counts = [], {}, {}
    for path, text in items:
        if len(text) < min_chars:
            continue
        key = tuple(path)
        if not path:
            section = "lead"
        else:
            section = section_ids.setdefault(key, f"s{len(section_ids) + 1}")
        counts[section] = counts.get(section, 0) + 1
        passages.append({"passage_id": f"{section}.p{counts[section]}", "kind": "abstract" if not path else "paragraph",
                         "section_path": list(path), "text": text})
    return passages


def html_passages(html: str, *, title: str | None = None, min_chars: int = 40) -> list[dict[str, Any]]:
    collector = _Collector()
    collector.feed(html)
    collector.close()
    collector._flush()
    passages = _number(collector.items, min_chars)
    if title:
        passages.insert(0, {"passage_id": "title", "kind": "title", "section_path": [], "text": title})
    return passages


_MD_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")


def text_passages(text: str, *, title: str | None = None, min_chars: int = 40) -> list[dict[str, Any]]:
    """Plain or Markdown text: blank lines separate paragraphs, `#` lines are headings."""
    items, path = [], []
    for block in re.split(r"\n\s*\n", text.replace("\r\n", "\n")):
        lines = [l for l in block.strip().split("\n") if l.strip()]
        if not lines:
            continue
        heading = _MD_HEADING.match(lines[0])
        if heading:
            level = len(heading.group(1))
            path = path[: level - 1] + [heading.group(2).strip()]
            lines = lines[1:]
            if not lines:
                continue
        paragraph = _SPACE.sub(" ", " ".join(lines)).strip()
        if paragraph and not (path and _BACK_MATTER.match(path[0])):
            items.append((list(path), paragraph))
    passages = _number(items, min_chars)
    if title:
        passages.insert(0, {"passage_id": "title", "kind": "title", "section_path": [], "text": title})
    return passages
