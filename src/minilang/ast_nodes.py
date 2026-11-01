"""Abstract syntax tree."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Node:
    line: int = field(default=0, kw_only=True)


# expressions
@dataclass
class Literal(Node):
    value: Any = None            # int, float, bool or str


@dataclass
class Var(Node):
    name: str = ""


@dataclass
class Unary(Node):
    op: str = ""
    operand: Node | None = None


@dataclass
class Binary(Node):
    op: str = ""
    left: Node | None = None
    right: Node | None = None


@dataclass
class Call(Node):
    name: str = ""
    args: list[Node] = field(default_factory=list)


# statements
@dataclass
class Let(Node):
    name: str = ""
    init: Node | None = None


@dataclass
class Assign(Node):
    name: str = ""
    value: Node | None = None


@dataclass
class ExprStmt(Node):
    expr: Node | None = None


@dataclass
class Block(Node):
    stmts: list[Node] = field(default_factory=list)


@dataclass
class If(Node):
    cond: Node | None = None
    then: Block | None = None
    otherwise: Node | None = None      # Block or If


@dataclass
class While(Node):
    cond: Node | None = None
    body: Block | None = None


@dataclass
class Return(Node):
    value: Node | None = None


@dataclass
class Break(Node):
    pass


@dataclass
class Continue(Node):
    pass


@dataclass
class FnDecl(Node):
    name: str = ""
    params: list[str] = field(default_factory=list)
    body: Block | None = None


@dataclass
class Program(Node):
    stmts: list[Node] = field(default_factory=list)


def dump(node: Any, indent: int = 0) -> str:
    """Readable indented dump of an AST."""
    pad = "  " * indent
    if isinstance(node, list):
        return "".join(dump(n, indent) for n in node)
    if not isinstance(node, Node):
        return f"{pad}{node!r}\n"
    scalars = {k: v for k, v in vars(node).items() if k != "line" and not isinstance(v, (Node, list)) and v is not None}
    head = f"{pad}{type(node).__name__}" + (f" {scalars}" if scalars else "") + "\n"
    kids = "".join(dump(v, indent + 1) for k, v in vars(node).items() if isinstance(v, (Node, list)) and v)
    return head + kids
