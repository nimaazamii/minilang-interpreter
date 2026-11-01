import unittest
from pathlib import Path

from minilang import (LexError, MiniRuntimeError, ParseError, SemanticError, dump, parse, run, tokenize)

PROGRAMS = Path(__file__).resolve().parents[1] / "examples" / "programs"


def out(src, **kw):
    return run(src, **kw)


def sem_errors(src):
    with unittest.TestCase().assertRaises(SemanticError) as cm:
        run(src)
    return [e.message for e in cm.exception.errors]


class TestLexer(unittest.TestCase):
    def test_tokens_positions_and_aliases(self):
        toks = tokenize('let x = 3.5; # comment\nif a && !b {}')
        self.assertEqual([t.text for t in toks[:5]], ["let", "x", "=", "3.5", ";"])
        self.assertEqual([t.kind for t in toks[:5]], ["KEYWORD", "IDENT", "OP", "NUMBER", "OP"])
        self.assertEqual((toks[5].text, toks[5].line), ("if", 2))
        self.assertEqual([t.text for t in toks if t.kind == "KEYWORD"][-2:], ["and", "not"])
        self.assertEqual(toks[-1].kind, "EOF")

    def test_two_char_operators_and_strings(self):
        self.assertEqual([t.text for t in tokenize("a // b <= c != d")][:7], ["a", "//", "b", "<=", "c", "!=", "d"])
        self.assertEqual(tokenize(r'"a\n\"b\""')[0].text, 'a\n"b"')

    def test_lex_errors(self):
        for bad in ('"abc', "let x = @;", r'"bad \q"'):
            with self.assertRaises(LexError):
                tokenize(bad)
        with self.assertRaises(LexError) as cm:
            tokenize("a\n  $")
        self.assertEqual((cm.exception.line, cm.exception.col), (2, 3))


class TestParser(unittest.TestCase):
    def test_precedence_and_associativity(self):
        self.assertEqual(out("print(1 + 2 * 3, (1 + 2) * 3, 10 - 4 - 3, 2 * 3 % 4, -2 * 3);"), ["7 9 3 2 -6"])
        self.assertEqual(out("print(1 < 2 and 2 < 3 or false, not true == false);"), ["true true"])
        self.assertEqual(out("print(8 / 2 / 2, 7 // 2 * 2);"), ["2.0 6"])

    def test_dangling_else_and_else_if(self):
        src = "fn f(x) { if x < 0 { return \"neg\"; } else if x == 0 { return \"zero\"; } else { return \"pos\"; } }\nprint(f(-1), f(0), f(5));"
        self.assertEqual(out(src), ["neg zero pos"])

    def test_parse_errors_have_positions(self):
        cases = ["let x = ;", "let = 3;", "print(1;", "if true { print(1);", "fn f( { }", "1 +;", "{ fn g() {} }"]
        for src in cases:
            with self.assertRaises(ParseError, msg=src):
                parse(src)
        with self.assertRaises(ParseError) as cm:
            parse("let a = 1;\nlet b = ;")
        self.assertEqual(cm.exception.line, 2)

    def test_ast_dump_contains_structure(self):
        text = dump(parse("let x = 1 + 2 * 3;"))
        self.assertIn("Let", text)
        self.assertIn("Binary {'op': '+'}", text)
        self.assertLess(text.index("'+'"), text.index("'*'"))


class TestSemantics(unittest.TestCase):
    def test_collects_multiple_errors_sorted_by_line(self):
        errs = sem_errors("let a = 1;\nlet a = 2;\nb = 3;\nprint(c);\nbreak;\nreturn 1;")
        self.assertEqual(len(errs), 5)
        self.assertIn("already declared", errs[0])
        self.assertIn("undeclared variable 'b'", errs[1])

    def test_function_checks(self):
        self.assertTrue(any("expects 2" in e for e in sem_errors("fn f(a, b) { return a; } print(f(1));")))
        self.assertTrue(any("undefined function" in e for e in sem_errors("print(g(1));")))
        self.assertTrue(any("already defined" in e for e in sem_errors("fn f() {} fn f() {}")))
        self.assertTrue(any("already defined" in e for e in sem_errors("fn print() {}")))
        self.assertTrue(any("duplicate parameter" in e for e in sem_errors("fn f(a, a) {}")))
        self.assertTrue(any("'continue' outside" in e for e in sem_errors("fn f() { continue; }")))

    def test_static_type_errors(self):
        for src, fragment in [('let x = 1 + "a";', "cannot be applied"), ('let s = "a" - "b";', "cannot be applied"),
                              ("if 1 { }", "must be bool"), ('let x = 1 < "a";', "cannot compare"),
                              ("let x = 1; x = true;", "cannot assign"), ("let b = true; let c = -b;", "needs a number"),
                              ("let q = not 3;", "needs bool"), ("let q = 1 and true;", "needs bool")]:
            self.assertTrue(any(fragment in e for e in sem_errors(src)), src)

    def test_valid_programs_pass_and_scoping(self):
        self.assertEqual(out("let x = 1; { let x = 2; print(x); } print(x);"), ["2", "1"])
        self.assertEqual(out("let f = 1.5; f = 2; print(f);"), ["2"])             # int may widen into a float variable
        self.assertEqual(out("fn even(n) { if n == 0 { return true; } return odd(n - 1); }\n"
                             "fn odd(n) { if n == 0 { return false; } return even(n - 1); }\nprint(even(10));"), ["true"])
        self.assertEqual(out("let g = 10; fn read() { return g; } print(read());"), ["10"])


class TestExecution(unittest.TestCase):
    def test_reference_programs(self):
        def fib(n): return n if n < 2 else fib(n - 1) + fib(n - 2)
        src = "fn fib(n) { if n < 2 { return n; } return fib(n - 1) + fib(n - 2); }\nprint(fib(20));"
        self.assertEqual(out(src), [str(fib(20))])
        primes = sum(all(n % d for d in range(2, int(n ** 0.5) + 1)) for n in range(2, 1000))
        self.assertEqual(out((PROGRAMS / "primes.ml").read_text()), [f"primes below 1000: {primes}"])

    def test_collatz_program_against_python(self):
        def length(n):
            s = 0
            while n != 1:
                n = n // 2 if n % 2 == 0 else 3 * n + 1
                s += 1
            return s
        best = max(range(1, 3000), key=lambda i: (length(i), -i))
        result = out((PROGRAMS / "collatz.ml").read_text(), max_steps=5_000_000)
        self.assertEqual(result, [f"longest chain below 3000 starts at {best} with {length(best)} steps"])

    def test_gcd_and_arithmetic_semantics(self):
        self.assertEqual(out((PROGRAMS / "gcd_strings.ml").read_text()),
                         ["gcd(1071, 462) = 21", "Hello, MiniLang has 15 characters", "2.5 2 2 -4 5.0"])

    def test_loops_break_continue_return(self):
        src = """let total = 0; let i = 0;
                 while true { i = i + 1; if i > 10 { break; } if i % 2 == 0 { continue; } total = total + i; }
                 print(total);
                 fn first_big(limit) { let k = 1; while true { if k * k > limit { return k; } k = k + 1; } }
                 print(first_big(50));"""
        self.assertEqual(out(src), ["25", "8"])

    def test_short_circuit(self):
        src = "fn boom() { print(\"called\"); return true; }\nlet a = false and boom(); let b = true or boom(); print(a, b);"
        self.assertEqual(out(src), ["false true"])

    def test_strings_and_conversions(self):
        self.assertEqual(out('print("ab" < "b", "x" + "y", str(12) + "!", int("42") + 1, float(3), len("héllo"));'), ["true xy 12! 43 3.0 5"])
        self.assertEqual(out("print(true == 1, 1 == 1.0, \"a\" == \"a\");"), ["false true true"])

    def test_runtime_errors(self):
        for src, fragment in [("print(1 / 0);", "division by zero"), ("print(1 % 0);", "division by zero"),
                              ("fn f(x) { return x + 1; } print(f(\"a\"));", "cannot be applied"),
                              ("fn f(x) { if x { return 1; } return 2; } print(f(3));", "must be bool"),
                              ("print(int(\"abc\"));", "cannot convert"), ("fn f(n) { return f(n + 1); } f(0);", "call depth"),
                              ("fn f(x) { return len(x); } print(f(3));", "needs a string")]:
            with self.assertRaises(MiniRuntimeError, msg=src) as cm:
                run(src)
            self.assertIn(fragment, cm.exception.message)

    def test_step_limit_stops_infinite_loop(self):
        with self.assertRaises(MiniRuntimeError) as cm:
            run("while true { }", max_steps=10_000)
        self.assertIn("step limit", cm.exception.message)

    def test_runtime_error_reports_line(self):
        with self.assertRaises(MiniRuntimeError) as cm:
            run("let a = 1;\nlet b = 0;\nprint(a / b);")
        self.assertEqual(cm.exception.line, 3)

    def test_print_formats_and_return_value(self):
        self.assertEqual(out("print(); print(true, false, 1.5, \"s\");"), ["", "true false 1.5 s"])
        self.assertEqual(out("fn nothing() { return; } print(nothing() == nothing());"), ["true"])


if __name__ == "__main__":
    unittest.main()
