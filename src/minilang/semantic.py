"""Semantic analysis: scopes, arity, control-flow placement and a small static type check.

Static types: int, float, bool, str and 'any' (unknown, e.g. function parameters / results). A variable's type is
fixed by its initialiser; 'any' disables checking for that value.
"""
from __future__ import annotations

from . import ast_nodes as A
from .errors import MiniLangError, SemanticError

BUILTINS = {"print": (None, "any"), "len": (1, "int"), "str": (1, "str"), "int": (1, "int"), "float": (1, "float"), "abs": (1, "any")}
NUMERIC = {"int", "float"}


class Analyzer:
    def __init__(self) -> None:
        self.errors: list[MiniLangError] = []
        self.scopes: list[dict[str, str]] = [{}]
        self.functions: dict[str, int] = {}
        self.in_function = False
        self.loop_depth = 0

    def err(self, msg: str, node: A.Node) -> None:
        self.errors.append(MiniLangError(msg, node.line))

    # scopes
    def lookup(self, name: str) -> str | None:
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return None

    def analyze(self, program: A.Program) -> None:
        for s in program.stmts:                       # hoist function names (mutual recursion)
            if isinstance(s, A.FnDecl):
                if s.name in self.functions or s.name in BUILTINS:
                    self.err(f"function '{s.name}' is already defined", s)
                self.functions[s.name] = len(s.params)
        for s in program.stmts:
            if not isinstance(s, A.FnDecl):
                self.stmt(s)
        for s in program.stmts:                       # bodies see every global variable
            if isinstance(s, A.FnDecl):
                self.function(s)
        if self.errors:
            raise SemanticError(sorted(self.errors, key=lambda e: e.line or 0))

    def function(self, fn: A.FnDecl) -> None:
        self.in_function, saved = True, self.loop_depth
        self.loop_depth = 0
        params = {}
        for p in fn.params:
            if p in params:
                self.err(f"duplicate parameter '{p}'", fn)
            params[p] = "any"
        self.scopes.append(params)
        for s in fn.body.stmts:
            self.stmt(s)
        self.scopes.pop()
        self.in_function, self.loop_depth = False, saved

    def block(self, b: A.Block) -> None:
        self.scopes.append({})
        for s in b.stmts:
            self.stmt(s)
        self.scopes.pop()

    def stmt(self, s: A.Node) -> None:
        if isinstance(s, A.Let):
            t = self.infer(s.init)
            if s.name in self.scopes[-1]:
                self.err(f"variable '{s.name}' is already declared in this scope", s)
            self.scopes[-1][s.name] = t
        elif isinstance(s, A.Assign):
            target = self.lookup(s.name)
            t = self.infer(s.value)
            if target is None:
                self.err(f"assignment to undeclared variable '{s.name}'", s)
            elif target != "any" and t != "any" and not (t == target or (target == "float" and t == "int")):
                self.err(f"cannot assign {t} to variable '{s.name}' of type {target}", s)
        elif isinstance(s, A.ExprStmt):
            self.infer(s.expr)
        elif isinstance(s, A.Block):
            self.block(s)
        elif isinstance(s, A.If):
            self.condition(s.cond, "if")
            self.block(s.then)
            if isinstance(s.otherwise, A.If):
                self.stmt(s.otherwise)
            elif s.otherwise is not None:
                self.block(s.otherwise)
        elif isinstance(s, A.While):
            self.condition(s.cond, "while")
            self.loop_depth += 1
            self.block(s.body)
            self.loop_depth -= 1
        elif isinstance(s, A.Return):
            if not self.in_function:
                self.err("'return' outside of a function", s)
            if s.value is not None:
                self.infer(s.value)
        elif isinstance(s, (A.Break, A.Continue)):
            if self.loop_depth == 0:
                self.err(f"'{'break' if isinstance(s, A.Break) else 'continue'}' outside of a loop", s)

    def condition(self, e: A.Node, what: str) -> None:
        t = self.infer(e)
        if t not in ("bool", "any"):
            self.err(f"{what} condition must be bool, found {t}", e)

    def infer(self, e: A.Node) -> str:
        if isinstance(e, A.Literal):
            return {bool: "bool", int: "int", float: "float", str: "str"}[type(e.value)]
        if isinstance(e, A.Var):
            t = self.lookup(e.name)
            if t is None:
                self.err(f"use of undeclared variable '{e.name}'", e)
                return "any"
            return t
        if isinstance(e, A.Unary):
            t = self.infer(e.operand)
            if e.op == "-":
                if t not in NUMERIC | {"any"}:
                    self.err(f"unary '-' needs a number, found {t}", e)
                return t if t in NUMERIC else "any"
            if t not in ("bool", "any"):
                self.err(f"'not' needs bool, found {t}", e)
            return "bool"
        if isinstance(e, A.Binary):
            return self.binary(e)
        if isinstance(e, A.Call):
            arg_types = [self.infer(a) for a in e.args]
            if e.name in BUILTINS:
                arity, ret = BUILTINS[e.name]
                if arity is not None and arity != len(e.args):
                    self.err(f"'{e.name}' expects {arity} argument(s), got {len(e.args)}", e)
                return ret
            if e.name not in self.functions:
                self.err(f"call to undefined function '{e.name}'", e)
                return "any"
            if self.functions[e.name] != len(arg_types):
                self.err(f"'{e.name}' expects {self.functions[e.name]} argument(s), got {len(arg_types)}", e)
            return "any"
        return "any"

    def binary(self, e: A.Binary) -> str:
        lt, rt, op = self.infer(e.left), self.infer(e.right), e.op
        unknown = "any" in (lt, rt)
        if op in ("and", "or"):
            for t in (lt, rt):
                if t not in ("bool", "any"):
                    self.err(f"'{op}' needs bool operands, found {t}", e)
            return "bool"
        if op in ("==", "!="):
            return "bool"
        if op in ("<", "<=", ">", ">="):
            if not unknown and not ((lt in NUMERIC and rt in NUMERIC) or lt == rt == "str"):
                self.err(f"cannot compare {lt} with {rt}", e)
            return "bool"
        if op == "+" and lt == rt == "str":
            return "str"
        if not unknown and not (lt in NUMERIC and rt in NUMERIC):
            self.err(f"operator '{op}' cannot be applied to {lt} and {rt}", e)
            return "any"
        if unknown:
            return "any"
        if op == "/":
            return "float"
        return "float" if "float" in (lt, rt) else "int"


def analyze(program: A.Program) -> None:
    Analyzer().analyze(program)
