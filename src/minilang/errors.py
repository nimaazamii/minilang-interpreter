"""Error types carrying source positions."""
from __future__ import annotations


class MiniLangError(Exception):
    def __init__(self, message: str, line: int | None = None, col: int | None = None) -> None:
        self.message, self.line, self.col = message, line, col
        where = f"line {line}" + (f", col {col}" if col is not None else "") if line is not None else "?"
        super().__init__(f"{where}: {message}")


class LexError(MiniLangError):
    pass


class ParseError(MiniLangError):
    pass


class SemanticError(MiniLangError):
    """Raised with all collected semantic problems in ``errors``."""

    def __init__(self, errors: list[MiniLangError]) -> None:
        self.errors = errors
        super().__init__("; ".join(str(e) for e in errors) or "semantic error")


class MiniRuntimeError(MiniLangError):
    pass
