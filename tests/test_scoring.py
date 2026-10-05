import sys
import textwrap

import astroid
import pytest

from pylint_cognitive_complexity import cognitive_complexity


def score(body: str, header: str = "def f():") -> int:
    source = header + "\n" + textwrap.indent(textwrap.dedent(body), "    ")
    return cognitive_complexity(astroid.extract_node(source))


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        pytest.param("pass", 0, id="empty"),
        pytest.param("if a: pass", 1, id="if"),
        pytest.param(
            """
            if a:
                pass
            elif b:
                pass
            else:
                pass
            """,
            3,
            id="if-elif-else",
        ),
        pytest.param(
            """
            if a:
                pass
            else:
                if b:
                    pass
            """,
            4,
            id="else-if-is-nested-not-elif",
        ),
        pytest.param(
            """
            if a:
                pass
            elif b:
                if c:
                    pass
            """,
            4,
            id="elif-body-is-nested",
        ),
        pytest.param(
            """
            if a:
                if b:
                    if c:
                        pass
            """,
            6,
            id="nesting-penalty",
        ),
        pytest.param(
            """
            for x in a:
                if x:
                    break
            else:
                pass
            """,
            4,
            id="for-else-break",
        ),
        pytest.param(
            """
            while a:
                if b:
                    continue
            """,
            3,
            id="while-continue",
        ),
        pytest.param(
            """
            try:
                if a:
                    pass
            except ValueError:
                pass
            except TypeError:
                if b:
                    pass
            else:
                pass
            finally:
                if c:
                    pass
            """,
            7,
            id="try-except-else-finally",
        ),
        pytest.param(
            """
            try:
                pass
            except* ValueError:
                if a:
                    pass
            """,
            3,
            id="except-star",
            marks=pytest.mark.skipif(sys.version_info < (3, 11), reason="needs Python 3.11"),
        ),
        pytest.param(
            """
            match a:
                case 1 if b and c:
                    if d:
                        pass
                case _:
                    pass
            """,
            4,
            id="match-guard",
        ),
        pytest.param("return a if b else c", 1, id="ternary"),
        pytest.param("return a if b else (c if d else e)", 3, id="nested-ternary"),
        pytest.param(
            """
            if a:
                x = b if c else d
            """,
            3,
            id="ternary-in-if",
        ),
        pytest.param("return a and b and c", 1, id="and-sequence"),
        pytest.param("return a and b or c", 2, id="mixed-sequence"),
        pytest.param("return (a or b) and (c or d)", 3, id="parenthesised-sequences"),
        pytest.param("return a and (b and c)", 1, id="same-op-parenthesised"),
        pytest.param("return not (a and b)", 1, id="negated-sequence"),
        pytest.param("if a and b: pass", 2, id="if-with-sequence"),
        pytest.param(
            """
            def inner():
                if a:
                    pass
            """,
            2,
            id="nested-function",
        ),
        pytest.param("return lambda: a if b else c", 2, id="lambda"),
        pytest.param(
            """
            class C:
                x = a if b else c
            """,
            1,
            id="class-does-not-nest",
        ),
        pytest.param(
            """
            try:
                with a:
                    if b:
                        pass
            except E:
                pass
            """,
            2,
            id="try-and-with-do-not-nest",
        ),
    ],
)
def test_score(body: str, expected: int) -> None:
    assert score(body) == expected


def test_async_constructs() -> None:
    body = """
    async for x in a:
        async with x:
            if x:
                pass
    """
    assert score(body, header="async def f():") == 3


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        pytest.param(
            """
            names = [r.name for r in rows if r.active if r.score > threshold]
            pairs = {(k, r.id) for k in keys for r in rows if r.key == k}
            totals = {k: sum(r.score for r in rows if r.key == k) for k in keys}
            return names, pairs, totals
            """,
            0,
            id="filtered-and-nested-comprehensions",
        ),
        pytest.param("return [x for x in a if x and b]", 1, id="sequence-in-filter"),
        pytest.param("return [x if x else 0 for x in a]", 1, id="ternary-in-element"),
    ],
)
def test_comprehensions_add_nothing_themselves(body: str, expected: int) -> None:
    assert score(body) == expected
