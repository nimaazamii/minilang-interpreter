"""Runs every program in examples/programs and stores the output in results/program_outputs.txt.

    python examples/run_programs.py
"""
from __future__ import annotations

import time
from pathlib import Path

from minilang import Interpreter, analyze, parse

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "results"
OUT.mkdir(exist_ok=True)


def main() -> None:
    lines = []
    for path in sorted((HERE / "programs").glob("*.ml")):
        program = parse(path.read_text())
        analyze(program)
        interp = Interpreter(program, max_steps=5_000_000)
        t0 = time.perf_counter()
        result = interp.run()
        dt = time.perf_counter() - t0
        lines.append(f"== {path.name}  ({interp.steps} interpreter steps, {dt:.2f} s)")
        lines.extend(result)
    text = "\n".join(lines) + "\n"
    (OUT / "program_outputs.txt").write_text(text)
    print(text)


if __name__ == "__main__":
    main()
