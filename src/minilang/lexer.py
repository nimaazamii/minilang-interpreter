"""Tokenizer."""
from __future__ import annotations

from dataclasses import dataclass

from .errors import LexError

KEYWORDS = {"let", "fn", "if", "else", "while", "return", "break", "continue", "true", "false", "and", "or", "not"}
TWO_CHAR = {"==", "!=", "<=", ">=", "//", "&&", "||"}
ONE_CHAR = set("+-*/%<>=!(){},;")
ALIASES = {"&&": "and", "||": "or", "!": "not"}
ESCAPES = {"n": "\n", "t": "\t", '"': '"', "\\": "\\"}


@dataclass(frozen=True)
class Token:
    kind: str      # NUMBER, STRING, IDENT, KEYWORD, OP, EOF
    text: str
    line: int
    col: int


def tokenize(src: str) -> list[Token]:
    tokens: list[Token] = []
    i, line, col = 0, 1, 1
    n = len(src)

    def advance(k: int = 1) -> None:
        nonlocal i, line, col
        for _ in range(k):
            if src[i] == "\n":
                line, col = line + 1, 1
            else:
                col += 1
            i += 1

    while i < n:
        ch = src[i]
        if ch in " \t\r\n":
            advance()
        elif ch == "#":
            while i < n and src[i] != "\n":
                advance()
        elif ch.isdigit():
            start, sl, sc = i, line, col
            while i < n and src[i].isdigit():
                advance()
            if i + 1 < n and src[i] == "." and src[i + 1].isdigit():
                advance()
                while i < n and src[i].isdigit():
                    advance()
            tokens.append(Token("NUMBER", src[start:i], sl, sc))
        elif ch.isalpha() or ch == "_":
            start, sl, sc = i, line, col
            while i < n and (src[i].isalnum() or src[i] == "_"):
                advance()
            word = src[start:i]
            tokens.append(Token("KEYWORD" if word in KEYWORDS else "IDENT", word, sl, sc))
        elif ch == '"':
            sl, sc = line, col
            advance()
            chars: list[str] = []
            while True:
                if i >= n or src[i] == "\n":
                    raise LexError("unterminated string literal", sl, sc)
                if src[i] == '"':
                    advance()
                    break
                if src[i] == "\\":
                    if i + 1 >= n or src[i + 1] not in ESCAPES:
                        raise LexError("invalid escape sequence", line, col)
                    chars.append(ESCAPES[src[i + 1]])
                    advance(2)
                else:
                    chars.append(src[i])
                    advance()
            tokens.append(Token("STRING", "".join(chars), sl, sc))
        else:
            two = src[i:i + 2]
            if two in TWO_CHAR:
                text, size = two, 2
            elif ch in ONE_CHAR:
                text, size = ch, 1
            else:
                raise LexError(f"unexpected character {ch!r}", line, col)
            sl, sc = line, col
            advance(size)
            if text in ALIASES:
                tokens.append(Token("KEYWORD", ALIASES[text], sl, sc))
            else:
                tokens.append(Token("OP", text, sl, sc))
    tokens.append(Token("EOF", "", line, col))
    return tokens
