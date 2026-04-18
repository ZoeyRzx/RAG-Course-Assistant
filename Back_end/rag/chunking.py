from __future__ import annotations

from dataclasses import dataclass

from .models import ChunkRecord, ParsedDocument, TextBlock
from .utils import first_non_empty, token_count, tokenize


@dataclass
class _PreparedBlock:
    text: str
    page: int | None
    section: str | None
    token_count: int


class Chunker:
    def __init__(self, target_tokens: int = 600, max_tokens: int = 800, overlap_tokens: int = 80):
        if target_tokens <= 0 or max_tokens <= 0 or overlap_tokens < 0:
            raise ValueError("Chunk sizes must be positive.")
        if target_tokens > max_tokens:
            raise ValueError("target_tokens must be <= max_tokens.")

        self.target_tokens = target_tokens
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens

    def chunk_document(self, document: ParsedDocument) -> list[ChunkRecord]:
        prepared_blocks = self._prepare_blocks(document.blocks)
        if not prepared_blocks:
            return []

        chunks: list[ChunkRecord] = []
        buffer: list[_PreparedBlock] = []
        buffer_tokens = 0

        for block in prepared_blocks:
            if buffer and buffer_tokens >= self.target_tokens:
                self._append_chunk(chunks, document, buffer)
                buffer = self._overlap_blocks(buffer)
                buffer_tokens = sum(item.token_count for item in buffer)
                while buffer and buffer_tokens + block.token_count > self.max_tokens:
                    buffer.pop(0)
                    buffer_tokens = sum(item.token_count for item in buffer)

            if buffer and buffer_tokens + block.token_count > self.max_tokens:
                self._append_chunk(chunks, document, buffer)
                buffer = self._overlap_blocks(buffer)
                buffer_tokens = sum(item.token_count for item in buffer)
                while buffer and buffer_tokens + block.token_count > self.max_tokens:
                    buffer.pop(0)
                    buffer_tokens = sum(item.token_count for item in buffer)

            buffer.append(block)
            buffer_tokens += block.token_count

        if buffer:
            self._append_chunk(chunks, document, buffer)

        return chunks

    def _prepare_blocks(self, blocks: list[TextBlock]) -> list[_PreparedBlock]:
        prepared: list[_PreparedBlock] = []
        for block in blocks:
            text = block.text.strip()
            if not text:
                continue

            block_tokens = token_count(text)
            if block_tokens <= self.max_tokens:
                prepared.append(
                    _PreparedBlock(
                        text=text,
                        page=block.page,
                        section=block.section,
                        token_count=block_tokens,
                    )
                )
                continue

            tokens = tokenize(text)
            step = max(1, self.max_tokens - min(self.overlap_tokens, self.max_tokens // 4))
            start = 0
            while start < len(tokens):
                window = tokens[start : start + self.max_tokens]
                if not window:
                    break
                prepared.append(
                    _PreparedBlock(
                        text=" ".join(window),
                        page=block.page,
                        section=block.section,
                        token_count=len(window),
                    )
                )
                start += step

        return prepared

    def _overlap_blocks(self, blocks: list[_PreparedBlock]) -> list[_PreparedBlock]:
        if self.overlap_tokens <= 0:
            return []

        overlap: list[_PreparedBlock] = []
        tokens = 0
        for block in reversed(blocks):
            overlap.insert(0, block)
            tokens += block.token_count
            if tokens >= self.overlap_tokens:
                break
        return overlap

    def _append_chunk(
        self,
        chunks: list[ChunkRecord],
        document: ParsedDocument,
        blocks: list[_PreparedBlock],
    ) -> None:
        text = "\n\n".join(block.text for block in blocks).strip()
        if not text:
            return
        if chunks and chunks[-1].text == text:
            return

        pages = [block.page for block in blocks if block.page is not None]
        sections = [block.section for block in blocks if block.section]
        page_start = min(pages) if pages else None
        page_end = max(pages) if pages else None
        section = self._resolve_section(sections)

        chunk = ChunkRecord(
            chunk_id=f"{document.doc_id}:{len(chunks):04d}",
            doc_id=document.doc_id,
            title=document.title,
            text=text,
            chunk_index=len(chunks),
            page_start=page_start,
            page_end=page_end,
            section=section,
            token_count=sum(block.token_count for block in blocks),
            metadata={
                "source_path": document.source_path,
                "doc_type": document.doc_type,
                "page_count": document.page_count,
                "section": section,
                "page_start": page_start,
                "page_end": page_end,
                "first_section": first_non_empty(sections),
            },
        )
        chunks.append(chunk)

    def _resolve_section(self, sections: list[str]) -> str | None:
        if not sections:
            return None
        unique_sections = [section for index, section in enumerate(sections) if section not in sections[:index]]
        if len(unique_sections) == 1:
            return unique_sections[0]
        return f"{unique_sections[0]} -> {unique_sections[-1]}"
