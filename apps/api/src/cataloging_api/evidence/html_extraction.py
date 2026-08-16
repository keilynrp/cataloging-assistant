"""Deterministic, JS-free HTML/XHTML -> text extraction using only the stdlib.

Never executes JavaScript (no engine is invoked anywhere in this module),
never resolves images/CSS/iframes/links, never issues a subrequest. Strips
script/style/noscript/template content entirely and keeps only visible text
from the remaining markup.
"""

from __future__ import annotations

from html.parser import HTMLParser

_SKIP_TAGS = {"script", "style", "noscript", "template"}
_BLOCK_TAGS = {
    "p",
    "div",
    "br",
    "li",
    "tr",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "section",
    "article",
    "header",
    "footer",
    "table",
    "ul",
    "ol",
    "blockquote",
    "pre",
}


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self._chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _SKIP_TAGS:
            self._skip_depth += 1
        elif tag in _BLOCK_TAGS:
            self._chunks.append("\n")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _BLOCK_TAGS:
            self._chunks.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIP_TAGS:
            if self._skip_depth > 0:
                self._skip_depth -= 1
        elif tag in _BLOCK_TAGS:
            self._chunks.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0 and data:
            self._chunks.append(data)

    def text(self) -> str:
        raw = "".join(self._chunks)
        lines = (" ".join(line.split()) for line in raw.splitlines())
        return "\n".join(line for line in lines if line).strip()


def extract_html_text(body: bytes, *, encoding: str = "utf-8") -> str:
    """Convert an HTML/XHTML document's bytes to visible-text-only.

    Decodes with `errors="replace"`: real-world HTML is rarely strict
    UTF-8, and substituting invalid bytes with U+FFFD mirrors what a
    browser does rather than failing the whole fetch over a minor encoding
    mismatch. Callers that need strict decoding (text/plain) must not use
    this function; see `add_remote_evidence_source` for that split.
    """
    decoded = body.decode(encoding, errors="replace")
    parser = _TextExtractor()
    parser.feed(decoded)
    parser.close()
    return parser.text()
