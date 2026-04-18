from __future__ import annotations

from pathlib import Path

from .config import Settings
from .models import ParsedDocument, TextBlock
from .utils import paragraphs_from_text, stable_file_id


def _looks_like_heading(paragraph: str) -> bool:
    words = paragraph.split()
    if not 1 <= len(words) <= 12:
        return False
    if paragraph.endswith((".", "!", "?", ",")):
        return False

    alpha_words = [word for word in words if any(char.isalpha() for char in word)]
    if not alpha_words:
        return False

    uppercase_words = [word for word in alpha_words if word.isupper()]
    title_case_words = [word for word in alpha_words if word[:1].isupper()]
    return (
        len(uppercase_words) / len(alpha_words) >= 0.6
        or len(title_case_words) / len(alpha_words) >= 0.8
    )


class DocumentParser:
    def __init__(self, settings: Settings):
        self.settings = settings

    def parse(self, path: Path) -> ParsedDocument:
        suffix = path.suffix.lower()
        if suffix not in self.settings.supported_extensions:
            raise ValueError(f"Unsupported file type: {path.suffix}")

        if suffix == ".pdf":
            return self._parse_pdf(path)
        if suffix == ".md":
            return self._parse_markdown(path)
        return self._parse_text(path)

    def _parse_pdf(self, path: Path) -> ParsedDocument:
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise ImportError("PDF parsing requires the 'pypdf' package.") from exc

        content = path.read_bytes()
        doc_id = stable_file_id(path, content)
        with path.open("rb") as file_handle:
            reader = PdfReader(file_handle)

            blocks: list[TextBlock] = []
            current_section: str | None = None
            block_index = 0

            for page_number, page in enumerate(reader.pages, start=1):
                page_text = page.extract_text() or ""
                for paragraph in paragraphs_from_text(page_text):
                    if _looks_like_heading(paragraph):
                        current_section = paragraph
                    blocks.append(
                        TextBlock(
                            text=paragraph,
                            page=page_number,
                            section=current_section,
                            block_index=block_index,
                        )
                    )
                    block_index += 1

            raw_text = "\n\n".join(block.text for block in blocks)
            return ParsedDocument(
                doc_id=doc_id,
                title=path.stem,
                source_path=str(path.resolve()),
                doc_type="pdf",
                raw_text=raw_text,
                blocks=blocks,
                page_count=len(reader.pages),
                metadata={"file_name": path.name},
            )

    def _parse_markdown(self, path: Path) -> ParsedDocument:
        content = path.read_bytes()
        doc_id = stable_file_id(path, content)
        text = content.decode("utf-8", errors="ignore")

        current_section = path.stem
        blocks: list[TextBlock] = []
        paragraph_buffer: list[str] = []
        block_index = 0

        def flush_buffer() -> None:
            nonlocal block_index
            if not paragraph_buffer:
                return
            paragraph = " ".join(part.strip() for part in paragraph_buffer if part.strip()).strip()
            if paragraph:
                blocks.append(
                    TextBlock(
                        text=paragraph,
                        page=None,
                        section=current_section,
                        block_index=block_index,
                    )
                )
                block_index += 1
            paragraph_buffer.clear()

        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                flush_buffer()
                current_section = stripped.lstrip("#").strip() or current_section
                blocks.append(
                    TextBlock(
                        text=current_section,
                        page=None,
                        section=current_section,
                        block_index=block_index,
                    )
                )
                block_index += 1
                continue

            if not stripped:
                flush_buffer()
                continue

            paragraph_buffer.append(stripped)

        flush_buffer()
        raw_text = "\n\n".join(block.text for block in blocks)
        return ParsedDocument(
            doc_id=doc_id,
            title=path.stem,
            source_path=str(path.resolve()),
            doc_type="markdown",
            raw_text=raw_text,
            blocks=blocks,
            page_count=None,
            metadata={"file_name": path.name},
        )

    def _parse_text(self, path: Path) -> ParsedDocument:
        content = path.read_bytes()
        doc_id = stable_file_id(path, content)
        text = content.decode("utf-8", errors="ignore")

        section = path.stem
        blocks = [
            TextBlock(text=paragraph, page=None, section=section, block_index=index)
            for index, paragraph in enumerate(paragraphs_from_text(text))
        ]
        raw_text = "\n\n".join(block.text for block in blocks)
        return ParsedDocument(
            doc_id=doc_id,
            title=path.stem,
            source_path=str(path.resolve()),
            doc_type="text",
            raw_text=raw_text,
            blocks=blocks,
            page_count=None,
            metadata={"file_name": path.name},
        )
