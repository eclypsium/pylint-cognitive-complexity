import astroid
from pylint.interfaces import HIGH
from pylint.testutils import CheckerTestCase, MessageTest, set_config

from pylint_cognitive_complexity import CognitiveComplexityChecker

FIVE_IFS = """
def f(a, b, c, d, e):
    if a: pass
    if b: pass
    if c: pass
    if d: pass
    if e: pass
"""


def too_complex(node: astroid.nodes.FunctionDef, score: int, maximum: int = 4) -> MessageTest:
    return MessageTest(
        "too-cognitively-complex",
        node=node,
        args=(node.name, score, maximum),
        confidence=HIGH,
    )


class TestCognitiveComplexityChecker(CheckerTestCase):
    CHECKER_CLASS = CognitiveComplexityChecker

    def test_at_maximum_is_not_flagged(self) -> None:
        module = astroid.parse(FIVE_IFS.replace("    if e: pass\n", ""))
        with self.assertNoMessages():
            self.walk(module)

    def test_above_maximum_is_flagged(self) -> None:
        module = astroid.parse(FIVE_IFS)
        with self.assertAddsMessages(too_complex(module.body[0], 5), ignore_position=True):
            self.walk(module)

    @set_config(max_cognitive_complexity=5)
    def test_maximum_is_configurable(self) -> None:
        with self.assertNoMessages():
            self.walk(astroid.parse(FIVE_IFS))

    def test_async_function_is_checked(self) -> None:
        module = astroid.parse(FIVE_IFS.replace("def f", "async def f"))
        with self.assertAddsMessages(too_complex(module.body[0], 5), ignore_position=True):
            self.walk(module)

    def test_nested_function_is_reported_through_its_parent(self) -> None:
        module = astroid.parse(
            """
            def outer():
                def inner(a, b, c):
                    if a: pass
                    if b: pass
                    if c: pass
            """
        )
        with self.assertAddsMessages(too_complex(module.body[0], 6), ignore_position=True):
            self.walk(module)

    def test_methods_are_checked(self) -> None:
        module = astroid.parse("class C:\n" + FIVE_IFS.replace("\n", "\n    "))
        method = module.body[0].body[0]
        with self.assertAddsMessages(too_complex(method, 5), ignore_position=True):
            self.walk(module)

    def test_comprehension_heavy_function_is_not_flagged(self) -> None:
        module = astroid.parse(
            """
            def summarize(rows, keys, threshold):
                names = [r.name for r in rows if r.active if r.score > threshold]
                pairs = {(k, r.id) for k in keys for r in rows if r.key == k}
                totals = {k: sum(r.score for r in rows if r.key == k) for k in keys}
                return names, pairs, totals
            """
        )
        with self.assertNoMessages():
            self.walk(module)
