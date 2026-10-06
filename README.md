# pylint-cognitive-complexity

A pylint plugin that reports functions and methods whose
[cognitive complexity](https://www.sonarsource.com/docs/CognitiveComplexity.pdf)
is above a configurable maximum.

## Install

Install it into the environment that runs pylint, for example:

```bash
uv add --dev git+https://github.com/eclypsium/pylint-cognitive-complexity
```

## Usage

```bash
pylint --load-plugins=pylint_cognitive_complexity mypackage
```

or in `pyproject.toml`:

```toml
[tool.pylint.main]
load-plugins = ["pylint_cognitive_complexity"]

[tool.pylint.cognitive-complexity]
max-cognitive-complexity = 4
```

| Message | Symbol | Meaning |
|---|---|---|
| `R7001` | `too-cognitively-complex` | The function scores above `max-cognitive-complexity`. |

| Option | Default | Meaning |
|---|---|---|
| `max-cognitive-complexity` | `4` | Highest score that passes. |

Silence a single function with `# pylint: disable=too-cognitively-complex` on its
`def` line.

## Scoring

The rules follow the SonarSource specification as SonarPython applies it to
Python. `n` is the nesting level, which starts at 0 in a function body.

| Construct | Adds | Nesting inside it |
|---|---|---|
| `if`, ternary `x if c else y` | 1 + n | n + 1 |
| `elif` | 1 | n + 1 |
| `else` on `if`, `for`, `while` or `try` | 1 | n + 1 |
| `for`, `async for`, `while` | 1 + n | n + 1 |
| each `except` or `except*` clause | 1 + n | n + 1 |
| `match` | 1 + n | n + 1 in each case |
| each sequence of like boolean operators | 1 | n |
| nested `def`, `async def`, `lambda` | 0 | n + 1 |
| `try` body, `finally`, `with`, `class`, comprehensions, `break`, `continue` | 0 | n |

So `a and b and c` adds 1, while `a and b or c` adds 2.

A nested function counts toward the function that contains it, and is not
reported on its own. Recursion is not counted.

### Comprehensions

A comprehension's `for` and `if` clauses add nothing and do not nest. A
comprehension is a declarative shorthand for a loop, so it reads as one step.
Cyclomatic complexity, as radon measures it, charges 1 per `for` plus 1 per `if`.
That lets a few readable comprehensions push a straight-line function out of
radon's rank A. Boolean operators or ternaries written inside a comprehension
still count, the same as anywhere else.

## Why the default is 4

The default is meant to pass the same functions as radon's rank `A (4)`, that is
a cyclomatic complexity of at most 4. The two metrics have no exact conversion,
so the threshold was calibrated by measurement.

Both metrics were computed for every function in the CPython standard library
and a large set of third-party packages. Each threshold was then scored on how
often "cognitive complexity ≤ T" agreed with "radon CC ≤ 4". T = 4 gave the
highest agreement, and it also flagged about the same share of functions as
radon does. T = 4 still came out best when radon's comprehension increments were
subtracted first.

To repeat the measurement, run:

```bash
uv run scripts/calibrate.py [DIR ...]
```

With no directories, it measures the running interpreter's standard library and
site-packages. For each threshold it prints the share of functions flagged, the
agreement with radon, and Cohen's kappa, and it marks the best threshold.
