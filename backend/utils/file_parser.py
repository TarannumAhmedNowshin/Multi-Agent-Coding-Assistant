"""Parse source code files into structured code chunks for indexing."""

import ast
import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

# Extensions we know how to parse
SUPPORTED_EXTENSIONS: set[str] = {
    ".py", ".js", ".ts", ".jsx", ".tsx",
    ".java", ".go", ".rs", ".rb", ".php",
    ".c", ".cpp", ".h", ".hpp", ".cs",
    ".md", ".txt", ".yaml", ".yml", ".toml", ".json",
}


@dataclass
class CodeChunk:
    """A single chunk of source code with metadata."""

    file_path: str
    start_line: int
    end_line: int
    chunk_type: str  # "function", "class", "method", "module", "block"
    name: str  # identifier or filename for whole-file chunks
    content: str
    language: str
    metadata: dict[str, str] = field(default_factory=dict)


def _detect_language(path: Path) -> str:
    """Map file extension to language name."""
    ext_map = {
        ".py": "python", ".js": "javascript", ".ts": "typescript",
        ".jsx": "javascript", ".tsx": "typescript",
        ".java": "java", ".go": "go", ".rs": "rust",
        ".rb": "ruby", ".php": "php",
        ".c": "c", ".cpp": "cpp", ".h": "c", ".hpp": "cpp", ".cs": "csharp",
        ".md": "markdown", ".txt": "text",
        ".yaml": "yaml", ".yml": "yaml", ".toml": "toml", ".json": "json",
    }
    return ext_map.get(path.suffix.lower(), "text")


def _get_source_segment(lines: list[str], start: int, end: int) -> str:
    """Extract lines from source (1-indexed start/end)."""
    return "".join(lines[start - 1 : end])


# ── Python AST Parser ────────────────────────────────────────────


def _parse_python(source: str, file_path: str) -> list[CodeChunk]:
    """Parse a Python file using AST to extract functions and classes."""
    chunks: list[CodeChunk] = []
    lines = source.splitlines(keepends=True)

    try:
        tree = ast.parse(source, filename=file_path)
    except SyntaxError:
        logger.warning("Syntax error parsing %s — treating as raw text", file_path)
        return _parse_raw(source, file_path, "python")

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            end_line = node.end_lineno or node.lineno
            chunks.append(CodeChunk(
                file_path=file_path,
                start_line=node.lineno,
                end_line=end_line,
                chunk_type="function",
                name=node.name,
                content=_get_source_segment(lines, node.lineno, end_line),
                language="python",
                metadata={"decorators": ", ".join(
                    ast.dump(d) for d in node.decorator_list
                )},
            ))
        elif isinstance(node, ast.ClassDef):
            end_line = node.end_lineno or node.lineno
            # Extract the whole class
            chunks.append(CodeChunk(
                file_path=file_path,
                start_line=node.lineno,
                end_line=end_line,
                chunk_type="class",
                name=node.name,
                content=_get_source_segment(lines, node.lineno, end_line),
                language="python",
                metadata={"bases": ", ".join(
                    ast.dump(b) for b in node.bases
                )},
            ))
            # Also extract individual methods
            for item in ast.iter_child_nodes(node):
                if isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef):
                    m_end = item.end_lineno or item.lineno
                    chunks.append(CodeChunk(
                        file_path=file_path,
                        start_line=item.lineno,
                        end_line=m_end,
                        chunk_type="method",
                        name=f"{node.name}.{item.name}",
                        content=_get_source_segment(lines, item.lineno, m_end),
                        language="python",
                        metadata={"class": node.name},
                    ))

    # If nothing was extracted (e.g., a config file), return the whole file
    if not chunks:
        return _parse_raw(source, file_path, "python")

    return chunks


# ── Raw / Generic Parser ─────────────────────────────────────────


def _parse_raw(source: str, file_path: str, language: str) -> list[CodeChunk]:
    """Wrap an entire file as a single chunk (fallback parser)."""
    line_count = source.count("\n") + 1
    return [
        CodeChunk(
            file_path=file_path,
            start_line=1,
            end_line=line_count,
            chunk_type="module",
            name=Path(file_path).name,
            content=source,
            language=language,
        )
    ]


# ── JS/TS Regex-Based Parser ─────────────────────────────────────

import re

# Patterns to find top-level functions, classes, and arrow-function consts
_JS_PATTERNS = [
    # function declarations
    re.compile(
        r"^(?:export\s+)?(?:async\s+)?function\s+(\w+)",
        re.MULTILINE,
    ),
    # class declarations
    re.compile(
        r"^(?:export\s+)?class\s+(\w+)",
        re.MULTILINE,
    ),
    # const/let/var arrow functions
    re.compile(
        r"^(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\(",
        re.MULTILINE,
    ),
]


def _parse_js_ts(source: str, file_path: str, language: str) -> list[CodeChunk]:
    """Regex-based JS/TS parser — extracts blocks between top-level declarations."""
    lines = source.splitlines(keepends=True)

    # Collect all declaration start positions
    declarations: list[tuple[int, str, str]] = []  # (line_no, name, type)
    for pattern in _JS_PATTERNS:
        for match in pattern.finditer(source):
            line_no = source[:match.start()].count("\n") + 1
            name = match.group(1)
            chunk_type = "class" if "class" in match.group(0) else "function"
            declarations.append((line_no, name, chunk_type))

    if not declarations:
        return _parse_raw(source, file_path, language)

    declarations.sort(key=lambda d: d[0])
    chunks: list[CodeChunk] = []

    for i, (line_no, name, chunk_type) in enumerate(declarations):
        # End is next declaration start - 1, or end-of-file
        if i + 1 < len(declarations):
            end_line = declarations[i + 1][0] - 1
        else:
            end_line = len(lines)
        # Strip trailing blank lines
        while end_line > line_no and not lines[end_line - 1].strip():
            end_line -= 1

        chunks.append(CodeChunk(
            file_path=file_path,
            start_line=line_no,
            end_line=end_line,
            chunk_type=chunk_type,
            name=name,
            content=_get_source_segment(lines, line_no, end_line),
            language=language,
        ))

    return chunks


# ── Public API ────────────────────────────────────────────────────


def parse_file(file_path: str, source: str | None = None) -> list[CodeChunk]:
    """Parse a source file into code chunks.

    Args:
        file_path: Path to the file.
        source: File content. If None, reads from disk.

    Returns:
        List of CodeChunk objects.
    """
    path = Path(file_path)
    language = _detect_language(path)

    if source is None:
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            logger.error("Cannot read file: %s", file_path)
            return []

    if not source.strip():
        return []

    if language == "python":
        return _parse_python(source, file_path)
    elif language in ("javascript", "typescript"):
        return _parse_js_ts(source, file_path, language)
    else:
        return _parse_raw(source, file_path, language)
