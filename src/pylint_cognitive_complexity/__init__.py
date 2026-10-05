"""Pylint plugin reporting functions with high cognitive complexity."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import TYPE_CHECKING, Any

from astroid import nodes
from pylint.checkers import BaseChecker
from pylint.checkers.utils import only_required_for_messages
from pylint.interfaces import HIGH

if TYPE_CHECKING:
    from pylint.lint import PyLinter


def cognitive_complexity(node: nodes.FunctionDef) -> int:
    """Return the cognitive complexity of a function, nested functions included."""
    return _block(node.body, 0)


def is_nested(node: nodes.FunctionDef) -> bool:
    """Tell whether ``node`` is scored as part of an enclosing function."""
    return any(isinstance(a, (nodes.FunctionDef, nodes.Lambda)) for a in node.node_ancestors())


def _block(stmts: Iterable[nodes.NodeNG], nesting: int) -> int:
    return sum(_score(stmt, nesting) for stmt in stmts)


def _score(node: nodes.NodeNG, nesting: int) -> int:
    return _HANDLERS.get(type(node), _generic)(node, nesting)


def _generic(node: nodes.NodeNG, nesting: int) -> int:
    return _block(node.get_children(), nesting)


def _else(stmts: list[nodes.NodeNG], nesting: int) -> int:
    return 1 + _block(stmts, nesting + 1) if stmts else 0


def _has_elif(node: nodes.If) -> bool:
    # astroid builds `elif` and `else: if` alike; only `elif` starts at the parent's column.
    return node.has_elif_block() and node.orelse[0].col_offset == node.col_offset


def _if(node: nodes.If, nesting: int) -> int:
    return 1 + nesting + _if_branches(node, nesting)


def _if_branches(node: nodes.If, nesting: int) -> int:
    score = _score(node.test, nesting) + _block(node.body, nesting + 1)
    if _has_elif(node):
        return score + 1 + _if_branches(node.orelse[0], nesting)
    return score + _else(node.orelse, nesting)


def _for(node: nodes.For, nesting: int) -> int:
    head = _block((node.target, node.iter), nesting)
    return 1 + nesting + head + _block(node.body, nesting + 1) + _else(node.orelse, nesting)


def _while(node: nodes.While, nesting: int) -> int:
    head = _score(node.test, nesting)
    return 1 + nesting + head + _block(node.body, nesting + 1) + _else(node.orelse, nesting)


def _try(node: nodes.Try | nodes.TryStar, nesting: int) -> int:
    return (
        _block(node.body, nesting)
        + _block(node.handlers, nesting)
        + _else(node.orelse, nesting)
        + _block(node.finalbody, nesting)
    )


def _except(node: nodes.ExceptHandler, nesting: int) -> int:
    head = _score(node.type, nesting) if node.type else 0
    return 1 + nesting + head + _block(node.body, nesting + 1)


def _match(node: nodes.Match, nesting: int) -> int:
    return 1 + nesting + _score(node.subject, nesting) + _block(node.cases, nesting)


def _case(node: nodes.MatchCase, nesting: int) -> int:
    guard = _score(node.guard, nesting) if node.guard else 0
    return guard + _block(node.body, nesting + 1)


def _ifexp(node: nodes.IfExp, nesting: int) -> int:
    return 1 + nesting + _generic(node, nesting + 1)


def _boolop(node: nodes.BoolOp, nesting: int) -> int:
    continues_sequence = isinstance(node.parent, nodes.BoolOp) and node.parent.op == node.op
    return int(not continues_sequence) + _generic(node, nesting)


def _function(node: nodes.FunctionDef, nesting: int) -> int:
    return _block(node.body, nesting + 1)


def _lambda(node: nodes.Lambda, nesting: int) -> int:
    return _score(node.body, nesting + 1)


_HANDLERS: dict[type[nodes.NodeNG], Callable[[Any, int], int]] = {
    nodes.If: _if,
    nodes.For: _for,
    nodes.AsyncFor: _for,
    nodes.While: _while,
    nodes.Try: _try,
    nodes.TryStar: _try,
    nodes.ExceptHandler: _except,
    nodes.Match: _match,
    nodes.MatchCase: _case,
    nodes.IfExp: _ifexp,
    nodes.BoolOp: _boolop,
    nodes.FunctionDef: _function,
    nodes.AsyncFunctionDef: _function,
    nodes.Lambda: _lambda,
}


class CognitiveComplexityChecker(BaseChecker):
    """Reports functions whose cognitive complexity exceeds the configured maximum."""

    name = "cognitive-complexity"
    msgs = {
        "R7001": (
            "'%s' is too cognitively complex (%d/%d)",
            "too-cognitively-complex",
            "Used when a function or method has a higher cognitive complexity "
            "than max-cognitive-complexity allows.",
        )
    }
    options = (
        (
            "max-cognitive-complexity",
            {
                "default": 4,
                "type": "int",
                "metavar": "<int>",
                "help": "Maximum cognitive complexity of a function or method.",
            },
        ),
    )

    @only_required_for_messages("too-cognitively-complex")
    def visit_functiondef(self, node: nodes.FunctionDef) -> None:
        """Report ``node`` if its cognitive complexity is above the maximum."""
        if is_nested(node):
            return
        complexity = cognitive_complexity(node)
        maximum = self.linter.config.max_cognitive_complexity
        if complexity > maximum:
            self.add_message(
                "too-cognitively-complex",
                node=node,
                confidence=HIGH,
                args=(node.name, complexity, maximum),
            )

    visit_asyncfunctiondef = visit_functiondef


def register(linter: PyLinter) -> None:
    """Register the checker with pylint."""
    linter.register_checker(CognitiveComplexityChecker(linter))
