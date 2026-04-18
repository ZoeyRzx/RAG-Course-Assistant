from __future__ import annotations

import hashlib
import re
import unicodedata
from pathlib import Path
from typing import Iterable


TOKEN_PATTERN = re.compile(r"\w+|[^\w\s]", re.UNICODE)
SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[.!?])\s+")


def normalize_inline_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def clean_multiline_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in text.split("\n")]
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def paragraphs_from_text(text: str) -> list[str]:
    cleaned = clean_multiline_text(text)
    if not cleaned:
        return []

    paragraphs: list[str] = []
    for raw_paragraph in re.split(r"\n\s*\n", cleaned):
        merged = normalize_inline_text(raw_paragraph.replace("\n", " "))
        if merged:
            paragraphs.append(merged)
    return paragraphs


def sentence_split(text: str) -> list[str]:
    normalized = normalize_inline_text(text)
    if not normalized:
        return []
    parts = [part.strip() for part in SENTENCE_SPLIT_PATTERN.split(normalized) if part.strip()]
    return parts or [normalized]


def tokenize(text: str) -> list[str]:
    return TOKEN_PATTERN.findall(text or "")


def token_count(text: str) -> int:
    return len(tokenize(text))


def truncate_text(text: str, max_chars: int) -> str:
    normalized = normalize_inline_text(text)
    if len(normalized) <= max_chars:
        return normalized
    return normalized[: max_chars - 3] + "..."


def stable_file_id(path: Path, content: bytes) -> str:
    digest = hashlib.sha1()
    digest.update(path.name.encode("utf-8", errors="ignore"))
    digest.update(content)
    return digest.hexdigest()[:16]


def first_non_empty(values: Iterable[str | None]) -> str | None:
    for value in values:
        if value:
            return value
    return None
