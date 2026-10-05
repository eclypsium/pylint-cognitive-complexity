"""Compare the plugin's cognitive complexity with radon's cyclomatic complexity."""

from __future__ import annotations

import argparse
import os
import sys
import sysconfig
from collections.abc import Iterable, Iterator
from pathlib import Path

import astroid
from astroid import nodes
from astroid.exceptions import AstroidError
from radon.complexity import cc_visit
from radon.visitors import Class

from pylint_cognitive_complexity import cognitive_complexity, is_nested

RADON_MAX = 4
THRESHOLDS = range(1, 11)
# Test suites are mostly trivial functions; nested package dirs would repeat a root.
SKIPPED_DIRS = {"test", "tests", "site-packages", "dist-packages", "__pycache__"}
# radon scores nested functions and classes separately, and lambdas inline.
RADON_SCOPES = (nodes.FunctionDef, nodes.ClassDef)
UNPARSABLE = (OSError, SyntaxError, UnicodeDecodeError, ValueError, RecursionError, AstroidError)

Row = tuple[int, int, int]


def iter_sources(roots: Iterable[Path]) -> Iterator[Path]:
    """Yield the Python files under ``roots``."""
    for root in roots:
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIPPED_DIRS]
            yield from (Path(dirpath, f) for f in filenames if f.endswith(".py"))


def radon_scores(source: str) -> dict[tuple[int, str], int]:
    """Map (def line, name) to radon's cyclomatic complexity for every function."""
    scores = {}
    pending = list(cc_visit(source))
    while pending:
        block = pending.pop()
        if isinstance(block, Class):
            pending.extend(block.methods + block.inner_classes)
        else:
            scores[block.lineno, block.name] = block.complexity
    return scores


def comprehension_increments(node: nodes.NodeNG) -> int:
    """Return what radon adds for the comprehensions in ``node``."""
    if isinstance(node, RADON_SCOPES):
        return 0
    own = 1 + len(node.ifs) if isinstance(node, nodes.Comprehension) else 0
    return own + sum(comprehension_increments(child) for child in node.get_children())


def measure(path: Path) -> list[Row]:
    """Return (radon CC, radon CC without comprehensions, cognitive) per reported function."""
    try:
        return list(_measure_source(path.read_text(encoding="utf-8")))
    except UNPARSABLE:
        return []


def _measure_source(source: str) -> Iterator[Row]:
    radon = radon_scores(source)
    for func in astroid.parse(source).nodes_of_class(nodes.FunctionDef):
        cc = radon.get((func.fromlineno, func.name))
        if cc is not None and not is_nested(func):
            comprehensions = sum(comprehension_increments(stmt) for stmt in func.body)
            yield cc, cc - comprehensions, cognitive_complexity(func)


def compare(reference: list[bool], flagged: list[bool]) -> tuple[float, float]:
    """Return the agreement and Cohen's kappa of two verdict lists."""
    total = len(reference)
    observed = sum(a == b for a, b in zip(reference, flagged, strict=True)) / total
    ref_rate, flag_rate = sum(reference) / total, sum(flagged) / total
    expected = ref_rate * flag_rate + (1 - ref_rate) * (1 - flag_rate)
    kappa = (observed - expected) / (1 - expected) if expected < 1 else float("nan")
    return observed, kappa


def report(rows: list[Row], column: int, label: str) -> None:
    """Print how well each cognitive threshold reproduces radon's CC <= RADON_MAX."""
    reference = [row[column] > RADON_MAX for row in rows]
    print(f"\n{label}: {len(rows)} functions, radon flags {sum(reference) / len(rows):.1%}")
    print(" T  flagged  agreement   kappa")
    results = []
    for threshold in THRESHOLDS:
        flagged = [row[2] > threshold for row in rows]
        results.append((threshold, sum(flagged) / len(rows), *compare(reference, flagged)))
    best = max(results, key=lambda result: result[3])
    for threshold, flag_rate, agreement, kappa in results:
        marker = "  <- best" if threshold == best[0] else ""
        print(f"{threshold:2d}  {flag_rate:7.1%}  {agreement:9.2%}  {kappa:6.3f}{marker}")


def main() -> None:
    """Measure the given roots and print one comparison table per radon variant."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "roots",
        nargs="*",
        type=Path,
        default=[Path(sysconfig.get_path("stdlib")), Path(sysconfig.get_path("purelib"))],
        help="directories to measure (default: the standard library and site-packages)",
    )
    rows = [row for path in iter_sources(parser.parse_args().roots) for row in measure(path)]
    if not rows:
        sys.exit("no functions found")
    report(rows, 0, "radon CC")
    report(rows, 1, "radon CC without comprehension increments")


if __name__ == "__main__":
    main()
