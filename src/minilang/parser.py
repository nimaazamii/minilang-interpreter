"""Recursive-descent parser with precedence climbing for expressions."""
from __future__ import annotations

from . import ast_nodes as A
from .errors import ParseError
from .lexer import Token, tokenize

BINARY_LEVELS = [["or"], ["and"], ["==", "!="], ["<", "<=", ">", ">="], ["+", "-"], ["*", "/", "//", "%"]]


class Parser:
    def __init__(self, tokens: list[Token]) -> None:
        self.toks, self.pos = tokens, 0

    # helpers
    @property
    def cur(self) -> Token:
        return self.toks[self.pos]

    def _is(self, text: str, kinds=("OP", "KEYWORD")) -> bool:
        return self.cur.kind in kinds and self.cur.text == text

    def _eat(self, text: str) -> Token:
        if not self._is(text):
            raise ParseError(f"expected '{text}' but found '{self.cur.text or 'end of input'}'", self.cur.line, self.cur.col)
        self.pos += 1
        return self.toks[self.pos - 1]

    def _ident(self, what: str) -> Token:
        if self.cur.kind != "IDENT":
            raise ParseError(f"expected {what}", self.cur.line, self.cur.col)
        self.pos += 1
        return self.toks[self.pos - 1]

    # program and statements
    def parse_program(self) -> A.Program:
        stmts = []
        while self.cur.kind != "EOF":
            stmts.append(self.statement(top_level=True))
        return A.Program(stmts, line=1)

    def block(self) -> A.Block:
        line = self._eat("{").line
        stmts = []
        while not self._is("}"):
            if self.cur.kind == "EOF":
                raise ParseError("unterminated block, expected '}'", self.cur.line, self.cur.col)
            stmts.append(self.statement())
        self._eat("}")
        return A.Block(stmts, line=line)

    def statement(self, top_level: bool = False) -> A.Node:
        t = self.cur
        if self._is("let"):
            self.pos += 1
            name = self._ident("variable name").text
            self._eat("=")
            init = self.expression()
            self._eat(";")
            return A.Let(name, init, line=t.line)
        if self._is("fn"):
            if not top_level:
                raise ParseError("functions may only be declared at top level", t.line, t.col)
            self.pos += 1
            name = self._ident("function name").text
            self._eat("(")
            params: list[str] = []
            if not self._is(")"):
                params.append(self._ident("parameter name").text)
                while self._is(","):
                    self.pos += 1
                    params.append(self._ident("parameter name").text)
            self._eat(")")
            return A.FnDecl(name, params, self.block(), line=t.line)
        if self._is("if"):
            return self.if_statement()
        if self._is("while"):
            self.pos += 1
            return A.While(self.expression(), self.block(), line=t.line)
        if self._is("return"):
            self.pos += 1
            value = None if self._is(";") else self.expression()
            self._eat(";")
            return A.Return(value, line=t.line)
        if self._is("break") or self._is("continue"):
            self.pos += 1
            self._eat(";")
            return A.Break(line=t.line) if t.text == "break" else A.Continue(line=t.line)
        if self._is("{"):
            return self.block()
        if t.kind == "IDENT" and self.toks[self.pos + 1].kind == "OP" and self.toks[self.pos + 1].text == "=":
            self.pos += 2
            value = self.expression()
            self._eat(";")
            return A.Assign(t.text, value, line=t.line)
        expr = self.expression()
        self._eat(";")
        return A.ExprStmt(expr, line=t.line)

    def if_statement(self) -> A.If:
        line = self._eat("if").line
        cond, then = self.expression(), self.block()
        otherwise = None
        if self._is("else"):
            self.pos += 1
            otherwise = self.if_statement() if self._is("if") else self.block()
        return A.If(cond, then, otherwise, line=line)

    # expressions
    def expression(self) -> A.Node:
        return self.binary(0)

    def binary(self, level: int) -> A.Node:
        if level == len(BINARY_LEVELS):
            return self.unary()
        left = self.binary(level + 1)
        while self.cur.kind in ("OP", "KEYWORD") and self.cur.text in BINARY_LEVELS[level]:
            op = self.cur
            self.pos += 1
            left = A.Binary(op.text, left, self.binary(level + 1), line=op.line)
        return left

    def unary(self) -> A.Node:
        t = self.cur
        if (t.kind == "OP" and t.text == "-") or (t.kind == "KEYWORD" and t.text == "not"):
            self.pos += 1
            return A.Unary(t.text, self.unary(), line=t.line)
        return self.call()

    def call(self) -> A.Node:
        t = self.cur
        if t.kind == "IDENT" and self.toks[self.pos + 1].kind == "OP" and self.toks[self.pos + 1].text == "(":
            self.pos += 2
            args: list[A.Node] = []
            if not self._is(")"):
                args.append(self.expression())
                while self._is(","):
                    self.pos += 1
                    args.append(self.expression())
            self._eat(")")
            return A.Call(t.text, args, line=t.line)
        return self.primary()

    def primary(self) -> A.Node:
        t = self.cur
        if t.kind == "NUMBER":
            self.pos += 1
            return A.Literal(float(t.text) if "." in t.text else int(t.text), line=t.line)
        if t.kind == "STRING":
            self.pos += 1
            return A.Literal(t.text, line=t.line)
        if t.kind == "KEYWORD" and t.text in ("true", "false"):
            self.pos += 1
            return A.Literal(t.text == "true", line=t.line)
        if t.kind == "IDENT":
            self.pos += 1
            return A.Var(t.text, line=t.line)
        if self._is("("):
            self.pos += 1
            e = self.expression()
            self._eat(")")
            return e
        raise ParseError(f"unexpected '{t.text or 'end of input'}'", t.line, t.col)


def parse(source: str) -> A.Program:
    return Parser(tokenize(source)).parse_program()
