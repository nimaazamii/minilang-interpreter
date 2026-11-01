"""Tree-walking interpreter with step and recursion limits."""
from __future__ import annotations

import math
import sys

from . import ast_nodes as A
from .errors import MiniRuntimeError
from .parser import parse
from .semantic import analyze


class _Break(Exception):
    pass


class _Continue(Exception):
    pass


class _Return(Exception):
    def __init__(self, value) -> None:
        self.value = value


class Env:
    def __init__(self, parent: "Env | None" = None) -> None:
        self.vars: dict = {}
        self.parent = parent

    def find(self, name: str):
        env = self
        while env is not None:
            if name in env.vars:
                return env
            env = env.parent
        return None


def fmt(v) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    return v if isinstance(v, str) else repr(v)


def _is_num(v) -> bool:
    return type(v) in (int, float)


class Interpreter:
    def __init__(self, program: A.Program, max_steps: int = 1_000_000, max_depth: int = 200) -> None:
        self.program, self.max_steps, self.max_depth = program, max_steps, max_depth
        self.output: list[str] = []
        self.steps = self.depth = 0
        self.functions = {s.name: s for s in program.stmts if isinstance(s, A.FnDecl)}
        self.globals = Env()

    def tick(self, node: A.Node) -> None:
        self.steps += 1
        if self.steps > self.max_steps:
            raise MiniRuntimeError("step limit exceeded (possible infinite loop)", node.line)

    def run(self) -> list[str]:
        old = sys.getrecursionlimit()
        sys.setrecursionlimit(max(old, 20000))
        try:
            for s in self.program.stmts:
                if not isinstance(s, A.FnDecl):
                    self.exec(s, self.globals)
        except (_Break, _Continue, _Return):
            pass
        finally:
            sys.setrecursionlimit(old)
        return self.output

    # statements
    def exec_block(self, stmts, env: Env) -> None:
        inner = Env(env)
        for s in stmts:
            self.exec(s, inner)

    def exec(self, s: A.Node, env: Env) -> None:
        self.tick(s)
        if isinstance(s, A.Let):
            env.vars[s.name] = self.eval(s.init, env)
        elif isinstance(s, A.Assign):
            target = env.find(s.name)
            if target is None:
                raise MiniRuntimeError(f"assignment to undefined variable '{s.name}'", s.line)
            target.vars[s.name] = self.eval(s.value, env)
        elif isinstance(s, A.ExprStmt):
            self.eval(s.expr, env)
        elif isinstance(s, A.Block):
            self.exec_block(s.stmts, env)
        elif isinstance(s, A.If):
            if self.cond(s.cond, env):
                self.exec_block(s.then.stmts, env)
            elif s.otherwise is not None:
                self.exec(s.otherwise, env)
        elif isinstance(s, A.While):
            while self.cond(s.cond, env):
                self.tick(s)
                try:
                    self.exec_block(s.body.stmts, env)
                except _Break:
                    break
                except _Continue:
                    continue
        elif isinstance(s, A.Return):
            raise _Return(None if s.value is None else self.eval(s.value, env))
        elif isinstance(s, A.Break):
            raise _Break()
        elif isinstance(s, A.Continue):
            raise _Continue()

    def cond(self, e: A.Node, env: Env) -> bool:
        v = self.eval(e, env)
        if not isinstance(v, bool):
            raise MiniRuntimeError(f"condition must be bool, found {type(v).__name__}", e.line)
        return v

    # expressions
    def eval(self, e: A.Node, env: Env):
        if isinstance(e, A.Literal):
            return e.value
        if isinstance(e, A.Var):
            owner = env.find(e.name)
            if owner is None:
                raise MiniRuntimeError(f"undefined variable '{e.name}'", e.line)
            return owner.vars[e.name]
        if isinstance(e, A.Unary):
            v = self.eval(e.operand, env)
            if e.op == "-":
                if not _is_num(v):
                    raise MiniRuntimeError("unary '-' needs a number", e.line)
                return -v
            if not isinstance(v, bool):
                raise MiniRuntimeError("'not' needs a bool", e.line)
            return not v
        if isinstance(e, A.Binary):
            return self.binary(e, env)
        if isinstance(e, A.Call):
            return self.call(e, env)
        raise MiniRuntimeError(f"cannot evaluate {type(e).__name__}", e.line)

    def binary(self, e: A.Binary, env: Env):
        op = e.op
        if op in ("and", "or"):                                   # short-circuit
            left = self.eval(e.left, env)
            if not isinstance(left, bool):
                raise MiniRuntimeError(f"'{op}' needs bool operands", e.line)
            if (op == "and" and not left) or (op == "or" and left):
                return left
            right = self.eval(e.right, env)
            if not isinstance(right, bool):
                raise MiniRuntimeError(f"'{op}' needs bool operands", e.line)
            return right
        a, b = self.eval(e.left, env), self.eval(e.right, env)
        if op == "==":
            return a == b and (isinstance(a, bool) == isinstance(b, bool))
        if op == "!=":
            return not (a == b and (isinstance(a, bool) == isinstance(b, bool)))
        if op == "+" and isinstance(a, str) and isinstance(b, str):
            return a + b
        if op in ("<", "<=", ">", ">=") and isinstance(a, str) and isinstance(b, str):
            return {"<": a < b, "<=": a <= b, ">": a > b, ">=": a >= b}[op]
        if not (_is_num(a) and _is_num(b)):
            raise MiniRuntimeError(f"operator '{op}' cannot be applied to {type(a).__name__} and {type(b).__name__}", e.line)
        if op in ("/", "//", "%") and b == 0:
            raise MiniRuntimeError("division by zero", e.line)
        return {"+": lambda: a + b, "-": lambda: a - b, "*": lambda: a * b, "/": lambda: a / b, "//": lambda: a // b,
                "%": lambda: a % b, "<": lambda: a < b, "<=": lambda: a <= b, ">": lambda: a > b, ">=": lambda: a >= b}[op]()

    def call(self, e: A.Call, env: Env):
        args = [self.eval(a, env) for a in e.args]
        self.tick(e)
        if e.name == "print":
            self.output.append(" ".join(fmt(a) for a in args))
            return None
        if e.name == "len":
            if not isinstance(args[0], str):
                raise MiniRuntimeError("len() needs a string", e.line)
            return len(args[0])
        if e.name == "str":
            return fmt(args[0])
        if e.name == "abs":
            if not _is_num(args[0]):
                raise MiniRuntimeError("abs() needs a number", e.line)
            return abs(args[0])
        if e.name in ("int", "float"):
            try:
                v = args[0]
                if isinstance(v, bool):
                    raise ValueError
                return int(v) if e.name == "int" else float(v)
            except (ValueError, TypeError, OverflowError):
                raise MiniRuntimeError(f"cannot convert {fmt(args[0])!r} with {e.name}()", e.line) from None
        fn = self.functions[e.name]
        if self.depth >= self.max_depth:
            raise MiniRuntimeError("maximum call depth exceeded", e.line)
        local = Env(self.globals)
        local.vars.update(zip(fn.params, args))
        self.depth += 1
        try:
            self.exec_block(fn.body.stmts, local)
        except _Return as r:
            return r.value
        finally:
            self.depth -= 1
        return None


def run(source: str, max_steps: int = 1_000_000, max_depth: int = 200) -> list[str]:
    """Parse, analyse and execute a program; returns the printed lines."""
    program = parse(source)
    analyze(program)
    return Interpreter(program, max_steps, max_depth).run()
