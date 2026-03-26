"""Code-aware text splitter with token counting and overlap."""

import logging

import tiktoken

from backend.utils.file_parser import CodeChunk

logger = logging.getLogger(__name__)

# Defaults tuned for text-embedding-3-small (8191 token context)
_DEFAULT_MAX_TOKENS = 512
_DEFAULT_OVERLAP_TOKENS = 64


class TextSplitter:
    """Split code chunks to fit within an embedding model's context window.

    Large chunks (functions, classes, whole files) are split into
    token-bounded sub-chunks with configurable overlap so that context
    is preserved across boundaries.
    """

    def __init__(
        self,
        max_tokens: int = _DEFAULT_MAX_TOKENS,
        overlap_tokens: int = _DEFAULT_OVERLAP_TOKENS,
    ) -> None:
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens
        self._enc = tiktoken.get_encoding("cl100k_base")

    def _token_len(self, text: str) -> int:
        return len(self._enc.encode(text))

    # ── Public API ────────────────────────────────────────────────

    def split_chunks(self, chunks: list[CodeChunk]) -> list[CodeChunk]:
        """Split a list of CodeChunks so every chunk fits within max_tokens.

        Small chunks are passed through unchanged; large ones are
        split on line boundaries with token overlap.
        """
        result: list[CodeChunk] = []
        for chunk in chunks:
            if self._token_len(chunk.content) <= self.max_tokens:
                result.append(chunk)
            else:
                result.extend(self._split_chunk(chunk))
        return result

    # ── Internal ──────────────────────────────────────────────────

    def _split_chunk(self, chunk: CodeChunk) -> list[CodeChunk]:
        """Split one oversized chunk on line boundaries."""
        lines = chunk.content.splitlines(keepends=True)
        sub_chunks: list[CodeChunk] = []

        start_idx = 0  # index into `lines`
        part = 0

        while start_idx < len(lines):
            # Greedily accumulate lines until we hit max_tokens
            current_lines: list[str] = []
            current_tokens = 0

            idx = start_idx
            while idx < len(lines):
                line_tokens = self._token_len(lines[idx])
                if current_tokens + line_tokens > self.max_tokens and current_lines:
                    break
                current_lines.append(lines[idx])
                current_tokens += line_tokens
                idx += 1

            content = "".join(current_lines)
            abs_start = chunk.start_line + start_idx
            abs_end = chunk.start_line + start_idx + len(current_lines) - 1

            sub_chunks.append(CodeChunk(
                file_path=chunk.file_path,
                start_line=abs_start,
                end_line=abs_end,
                chunk_type=chunk.chunk_type,
                name=f"{chunk.name}::part{part}",
                content=content,
                language=chunk.language,
                metadata={**chunk.metadata, "part": str(part)},
            ))
            part += 1

            # Advance with overlap (back up overlap_tokens worth of lines)
            if idx >= len(lines):
                break

            overlap_lines = 0
            overlap_tokens_acc = 0
            for back in range(len(current_lines) - 1, -1, -1):
                lt = self._token_len(current_lines[back])
                if overlap_tokens_acc + lt > self.overlap_tokens:
                    break
                overlap_tokens_acc += lt
                overlap_lines += 1

            start_idx = idx - overlap_lines

        return sub_chunks
