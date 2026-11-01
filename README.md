# minilang-interpreter

A small programming language with a complete front end and a tree-walking interpreter, written in Python:
**lexer, recursive-descent parser, AST, semantic analysis with static type checks, interpreter with step and recursion limits.**

## The language
```text
# comments start with '#'
let x = 10;                       # declaration; the initialiser fixes the static type (int, float, bool, str)
x = x + 1;                        # assignment (int may widen into a float variable)
fn gcd(a, b) { while b != 0 { let t = b; b = a % b; a = t; } return a; }
if x > 5 and not done { print("big", gcd(12, 18)); } else if x == 5 { print("five"); } else { print("small"); }
```
* Types: `int`, `float`, `bool`, `str`; operators `+ - * / // %`, comparisons, `==`, `!=`, `and`/`or`/`not` (also `&&`, `||`, `!`, short-circuit), unary `-`.
* `/` is true division, `//` floor division. Conditions must be `bool` (no implicit truthiness). Functions are global, may be mutually recursive, and take untyped parameters.
* Statements: `let`, assignment, `if/else if/else`, `while`, `break`, `continue`, `return`, blocks with lexical scope.
* Built-ins: `print`, `len`, `str`, `int`, `float`, `abs`.

## Pipeline
`tokenize` (positions, escapes, comments) -> `parse` (precedence climbing, error positions) -> `analyze` -> `Interpreter`.
The analyser collects **all** semantic errors sorted by line: undeclared/redeclared variables, wrong arity, unknown functions, `break`/`continue` outside loops, `return` outside functions,
and static type errors between known types (e.g. `1 + "a"`, `if 1 { }`, assigning `bool` to an `int` variable). Values of unknown type (`any`, e.g. parameters) are checked at run time instead.

## Installation and quick start
```bash
git clone https://github.com/nimaazamii/minilang-interpreter.git
cd minilang-interpreter
pip install -e ".[dev]"
pytest -q
```

```python
from minilang import run
print(run('''
fn fib(n) { if n < 2 { return n; } return fib(n - 1) + fib(n - 2); }
let i = 0;
while i < 5 { print(i, fib(i)); i = i + 1; }
'''))
```
Output:
```
['0 0', '1 1', '2 1', '3 2', '4 3']
```
`python examples/run_programs.py` runs `examples/programs/*.ml`; `minilang.dump(parse(src))` prints the AST.

## Verification (`pytest -q`, 21 tests)
Lexer positions and errors; precedence/associativity (`10 - 4 - 3`, `8 / 2 / 2`); error line numbers; multiple semantic errors in one pass; scoping and shadowing; mutual recursion;
short-circuit evaluation; runtime errors with line numbers (division by zero, type errors, depth limit, step limit for infinite loops);
programs whose results are compared with an **independent Python implementation** (Fibonacci, primes below 1000, longest Collatz chain below 3000).

## Example output (`results/program_outputs.txt`)
```
== collatz.ml  (955304 interpreter steps, 3.62 s)
longest chain below 3000 starts at 2919 with 216 steps
== gcd_strings.ml  (23 interpreter steps, 0.00 s)
gcd(1071, 462) = 21
Hello, MiniLang has 15 characters
2.5 2 2 -4 5.0
== primes.ml  (23188 interpreter steps, 0.10 s)
primes below 1000: 168
```
(The step count and times are from the build machine; the interpreter is a simple tree walker, roughly 0.3 million steps per second.)

## Limitations and future work
No arrays/records, first-class or nested functions, closures, or modules; error recovery stops at the first lexical/parse error. A compiler back end (for example LLVM IR generation) is **not** included:
no LLVM toolchain was available to validate generated code, so that part of the original plan remains open.

## References
* Nystrom, *Crafting Interpreters*; Aho, Lam, Sethi and Ullman, *Compilers: Principles, Techniques, and Tools*.

## License
MIT, see `LICENSE`.
